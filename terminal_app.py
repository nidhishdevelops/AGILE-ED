from agents import content_router, rag_agent, web_agent, youtube_search, email_agent, quiz_agent
import json
from config import Config
import logging
import re
from datetime import datetime
import concurrent.futures

# Initialize the result logger
from utils.result_logger import result_logger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('app.log')]
)
logger = logging.getLogger(__name__)

def handle_query(user_query):
    # Log query
    routing_info = content_router.determine_module_and_style(user_query)
    result_logger.log_query(user_query, routing_info)
    logger.info(f"Routing Info: {routing_info}")
    
    if not routing_info.get("in_domain", True):
        subject = f"Out-of-Domain: {routing_info['topic']}"
        body = f"Query: {user_query}\nTopic outside data science domain"
        email_sent = email_agent.send_notification(subject, body) if Config.EMAIL_PASSWORD else False
        
        message = "This topic is outside our data science domain."
        if email_sent:
            message += " We've notified our team!"
        
        result_logger.log_final_response({
            "status": "domain_error",
            "topic": routing_info["topic"],
            "message": message
        })
        
        return {
            "status": "domain_error",
            "message": message,
            "query": user_query,
            "topic": routing_info["topic"]
        }
    
    rag_result = rag_agent.retrieve_and_generate(
        routing_info["module"],
        routing_info["topic"],
        routing_info["style"]
    )
    
    # Debug logging for RAG results
    logger.info(f"RAG returned {len(rag_result.get('sources', []))} sources")
    logger.info(f"RAG response length: {len(rag_result.get('response', ''))} chars")
    logger.info(f"Selected LLM: {rag_result.get('llm_source', 'unknown')}")
    
    if rag_result.get("response") == "TOPIC_NOT_FOUND":
        subject = f"Missing Content: {routing_info['topic']}"
        body = f"Query: {user_query}\nModule: {routing_info['module']}"
        email_sent = email_agent.send_notification(subject, body) if Config.EMAIL_PASSWORD else False
        
        message = "This topic isn't in our system yet."
        if email_sent:
            message += " We've notified our team!"
        
        result_logger.log_final_response({
            "status": "error",
            "topic": routing_info["topic"],
            "message": message
        })
        
        return {
            "status": "error",
            "message": message,
            "query": user_query,
            "topic": routing_info["topic"]
        }

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_advancements = executor.submit(web_agent.search_advancements, routing_info["topic"])
        future_papers = executor.submit(web_agent.search_research_papers, routing_info["topic"])
        future_videos = executor.submit(youtube_search.search_youtube_videos, routing_info["topic"])
        future_books = executor.submit(web_agent.search_reference_books, routing_info["topic"])
        
        advancements = future_advancements.result()
        research_papers = future_papers.result()
        videos = future_videos.result()
        reference_books_web = future_books.result()
    
    # Debug logging for web results
    logger.info(f"Advancements found: {len(advancements)}")
    logger.info(f"Research papers found: {len(research_papers)}")
    logger.info(f"Videos found: {len(videos)}")
    logger.info(f"Reference books found: {len(reference_books_web)}")
    
    # Log web content
    if advancements:
        result_logger.log_web_content("advancements", routing_info["topic"], advancements)
    if research_papers:
        result_logger.log_web_content("research_papers", routing_info["topic"], research_papers)
    if videos:
        result_logger.log_web_content("youtube_videos", routing_info["topic"], videos)
    if reference_books_web:
        result_logger.log_web_content("reference_books", routing_info["topic"], reference_books_web)
    
    final_response = {
        "status": "success",
        "query": user_query,
        "topic": routing_info["topic"],
        "module": routing_info["module"],
        "learning_style": routing_info["style"],
        "explanation": rag_result["response"],
        "sources": rag_result["sources"],
        "llm_used": rag_result["llm_source"],
        "recent_advancements": advancements,
        "research_papers": research_papers,
        "video_recommendations": videos,
        "reference_books_web": reference_books_web
    }
    
    result_logger.log_final_response(final_response)
    
    return final_response

def generate_quiz(topic, explanation):
    """Generate quiz based on topic and explanation"""
    generator = quiz_agent.QuizGenerator()
    quiz = generator.generate_quiz(topic, explanation)
    
    # Log quiz generation
    result_logger.log_quiz_generation(topic, quiz)
    
    return quiz

def take_quiz_interactive(quiz):
    """Interactive quiz taking function"""
    print(f"\n\033[1;35m{'='*80}")
    print(f"QUIZ: {quiz['topic']}")
    print(f"Difficulty: {quiz['difficulty']}")
    print(f"{'='*80}\033[0m\n")
    
    student_answers = {}
    
    for question in quiz["questions"]:
        print(f"\n\033[1;34mQuestion {question['id']} ({question['type'].replace('_', ' ').title()}):\033[0m")
        
        if question["type"] == "mcq":
            print(f"\n{question['question']}\n")
            for option, text in question["options"].items():
                print(f"  {option}) {text}")
            answer = input("\nYour answer (A/B/C/D): ").strip()
            
        elif question["type"] == "short_answer":
            print(f"\n{question['question']}")
            print(f"(Write 2-3 sentences)")
            answer = input("\nYour answer: ").strip()
            
        elif question["type"] == "true_false":
            print(f"\nStatement: {question['statement']}")
            answer = input("\nTrue or False? (T/F): ").strip()
            
        elif question["type"] == "fill_blanks":
            print(f"\n{question['text']}")
            print("\nFill in the blanks (comma-separated):")
            answer = input("Your answers: ").strip()
            
        elif question["type"] == "code_completion":
            print(f"\n{question['question']}")
            print(f"\nIncomplete code:\n{question['incomplete_code']}")
            print(f"\nExpected output: {question['expected_output']}")
            answer = input("\nYour completed code:\n").strip()
            
        elif question["type"] == "numerical_problem":
            print(f"\n{question['problem']}")
            answer = input("\nYour answer: ").strip()
            
        else:
            print(f"\n{question.get('question', 'Unknown question type')}")
            answer = input("\nYour answer: ").strip()
        
        student_answers[str(question['id'])] = answer
    
    return student_answers

def evaluate_and_send_assessment(quiz, student_answers, student_email):
    """Evaluate quiz and send assessment email"""
    evaluator = quiz_agent.QuizEvaluator()
    result = evaluator.evaluate_answers(quiz, student_answers, student_email)
    
    # Log quiz evaluation
    result_logger.log_quiz_evaluation(result, result["assessment"])
    
    # Send assessment email
    email_sent = quiz_agent.send_assessment_email(
        student_email,
        result["assessment"],
        result
    )
    
    return result, email_sent

def format_section(title, content):
    return f"\n\033[1;34m{title}:\033[0m\n{content}\n"

def print_response(response):
    if response["status"] != "success":
        print(f"\n\033[1;31m {response['message']}\033[0m")
        return
    
    print(f"\n\033[1;35m{'='*80}")
    print(f"RESPONSE FOR: {response['query']}")
    print(f"{'='*80}\033[0m")
    print(f"Topic: \033[1m{response['topic']}\033[0m | Module: \033[1m{response['module']}\033[0m")
    print(f"Learning Style: \033[1m{response['learning_style']}\033[0m | LLM: \033[1m{response['llm_used']}\033[0m")
    
    explanation = response['explanation']

    if response['sources']:
        for i, source in enumerate(response['sources']):
            marker = f"[Source {i+1}]"
            source_info = f"{source['original_file']} ({source['location']})"
            explanation = explanation.replace(marker, source_info)
    
    explanation = re.sub(r'#{2,}', '', explanation)
    explanation = re.sub(r'\*{2}(.*?)\*{2}', r'\1', explanation)
    explanation = re.sub(r'\*(.*?)\*', r'\1', explanation)
    
    print(format_section("Detailed Explanation", explanation))
    
    if response['sources']:
        sources_text = "Material References:\n"
        for i, source in enumerate(response['sources']):
            sources_text += f"\n\033[1m{i+1}. {source['original_file']}\033[0m"
            sources_text += f"\n    Location: {source['location']}"
            sources_text += f"\n    Content: {source['text']}\n"
        print(format_section("Source References", sources_text))
    
    if response.get('reference_books_web'):
        books_text = ""
        for i, book in enumerate(response['reference_books_web']):
            books_text += f"\n\033[1m{i+1}. {book['title']}\033[0m by {book['authors']} ({book['year']})"
            books_text += f"\n    Description: {book['description']}"
            books_text += f"\n    Link: {book['link']}\n"
        print(format_section("Recommended Reference Books", books_text))
    
    if response['recent_advancements']:
        advancements_text = ""
        for i, adv in enumerate(response['recent_advancements']):
            advancements_text += f"\n\033[1m{i+1}. {adv['title']}\033[0m ({adv['date']})"
            advancements_text += f"\n    Source: {adv['source']}"
            advancements_text += f"\n    Summary: {adv['summary']}"
            advancements_text += f"\n    Link: {adv['link']}\n"
        print(format_section("Recent Advancements", advancements_text))
    
    if response['research_papers']:
        papers_text = ""
        for i, paper in enumerate(response['research_papers']):
            papers_text += f"\n\033[1m{i+1}. {paper['title']}\033[0m ({paper['year']})"
            papers_text += f"\n    Authors: {paper['authors']}"
            papers_text += f"\n    Summary: {paper['summary']}"
            papers_text += f"\n    Link: {paper['link']}\n"
        print(format_section("Research Papers", papers_text))
    
    if response['video_recommendations']:
        videos_text = ""
        for i, video in enumerate(response['video_recommendations']):
            videos_text += f"\n\033[1m{i+1}. {video['title']}\033[0m"
            videos_text += f"\n    Channel: {video['channel']}"
            videos_text += f"\n    URL: https://youtu.be/{video['video_id']}\n"
        print(format_section("Recommended Videos", videos_text))
    
    print(f"\n\033[1;35m{'='*80}")
    print(f"Response generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\033[0m")

def main_interactive():
    """Interactive main function with quiz support"""
    print("\n\033[1;36m" + "="*80)
    print("PERSONALIZED LEARNING AI SYSTEM")
    print("="*80 + "\033[0m")
    
    last_response = None
    
    try:
        while True:
            print("\n\033[1;33mOptions:\033[0m")
            print("1. Ask a question")
            print("2. Take a quiz on recent topic")
            print("3. Exit")
            
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == "1":
                user_query = input("\nEnter your question: ").strip()
                response = handle_query(user_query)
                last_response = response
                print_response(response)
                
                if response["status"] == "success":
                    take_quiz = input("\nWould you like to take a quiz on this topic? (yes/no): ").strip().lower()
                    if take_quiz in ["yes", "y"]:
                        quiz = generate_quiz(response["topic"], response["explanation"])
                        
                        # Check if quiz has questions
                        if not quiz.get("questions"):
                            print("\n Could not generate AI questions. Using basic questions.")
                        
                        # Take quiz
                        student_answers = take_quiz_interactive(quiz)
                        
                        # Get student email for assessment
                        student_email = input("\nEnter your email for personalized assessment: ").strip()
                        
                        # Evaluate and send assessment
                        result, email_sent = evaluate_and_send_assessment(quiz, student_answers, student_email)
                        
                        # Show immediate feedback
                        print(f"\n\033[1;32mQuiz Results:\033[0m")
                        print(f"Score: {result['total_score']}/{result['max_score']} ({result['percentage']:.1f}%)")
                        print(f"Grade: {result['grade']}")
                        print(f"Mastery Level: {result['assessment']['mastery_level']}")
                        
                        if email_sent:
                            print(f"\n Personalized assessment sent to {student_email}")
                        else:
                            print(f"\n Could not send email. Check email configuration in .env file")
                            print(f"   Or check if you're using Gmail App Password instead of normal password")
            
            elif choice == "2":
                if not last_response or last_response["status"] != "success":
                    print("\nPlease ask a question first to generate a topic.")
                    continue
                
                quiz = generate_quiz(last_response["topic"], last_response["explanation"])
                
                # Check if quiz has questions
                if not quiz.get("questions"):
                    print("\n Could not generate AI questions. Using basic questions.")
                
                student_answers = take_quiz_interactive(quiz)
                
                student_email = input("\nEnter your email for personalized assessment: ").strip()
                result, email_sent = evaluate_and_send_assessment(quiz, student_answers, student_email)
                
                print(f"\n\033[1;32mQuiz Results:\033[0m")
                print(f"Score: {result['total_score']}/{result['max_score']} ({result['percentage']:.1f}%)")
                print(f"Grade: {result['grade']}")
                
                if email_sent:
                    print(f"\n Personalized assessment sent to {student_email}")
                else:
                    print(f"\n Could not send email. Check email configuration.")
            
            elif choice == "3":
                print("\nThank you for using Personalized Learning AI System!")
                break
            
            else:
                print("\nInvalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print("\n\nExiting system...")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        # Save session results before exiting
        print("\n📊 Saving session results...")
        result_logger.save_session()
        print("✅ Results saved successfully!")

if __name__ == "__main__":
    main_interactive()