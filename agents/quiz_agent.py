import json
import re
import logging
from datetime import datetime
from typing import List, Dict, Tuple
from openai import OpenAI
from config import Config
import random

logger = logging.getLogger(__name__)
client = OpenAI(api_key=Config.OPENAI_API_KEY)

class QuizGenerator:
    def __init__(self):
        self.question_types = {
            "mcq": self.generate_mcq,
            "short_answer": self.generate_short_answer,
            "true_false": self.generate_true_false,
            "fill_blanks": self.generate_fill_blanks,
            "code_completion": self.generate_code_completion,
            "numerical_problem": self.generate_numerical_problem
        }
    
    def generate_quiz(self, topic: str, explanation: str, difficulty: str = "medium", num_questions: int = 5) -> Dict:
        """
        Generate a personalized quiz based on the topic and explanation
        """
        # Determine question mix based on topic and difficulty
        if "programming" in topic.lower() or "code" in topic.lower() or "python" in topic.lower():
            question_mix = ["mcq", "code_completion", "short_answer", "fill_blanks", "mcq"]
        elif "mathematics" in topic.lower() or "statistics" in topic.lower():
            question_mix = ["numerical_problem", "mcq", "short_answer", "true_false", "mcq"]
        else:
            question_mix = ["mcq", "short_answer", "true_false", "fill_blanks", "mcq"]
        
        quiz = {
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "difficulty": difficulty,
            "questions": []
        }
        
        # Generate questions
        for i, q_type in enumerate(question_mix[:num_questions]):
            if q_type in self.question_types:
                question = self.question_types[q_type](topic, explanation, difficulty, i+1)
                if question:
                    quiz["questions"].append(question)
        
        # If no questions generated, create fallback questions
        if not quiz["questions"]:
            quiz["questions"] = self.create_fallback_questions(topic)
        
        return quiz
    
    def create_fallback_questions(self, topic: str) -> List[Dict]:
        """Create simple fallback questions when AI generation fails"""
        return [
            {
                "id": 1,
                "type": "mcq",
                "question": f"What is the main purpose of understanding {topic}?",
                "options": {
                    "A": "To memorize facts",
                    "B": "To understand fundamental concepts",
                    "C": "To pass exams",
                    "D": "To write code"
                },
                "correct_answer": "B",
                "explanation": f"Understanding {topic} helps build foundational knowledge for more advanced concepts.",
                "difficulty_level": "easy",
                "concepts_tested": ["fundamentals"],
                "max_score": 2
            },
            {
                "id": 2,
                "type": "short_answer",
                "question": f"Explain {topic} in your own words.",
                "model_answer": f"{topic} refers to the classification and organization of information for effective processing and analysis.",
                "key_points": ["classification", "organization", "processing"],
                "rubric": {
                    "excellent": "Covers all key points with examples",
                    "good": "Covers most key points",
                    "poor": "Vague or incomplete explanation"
                },
                "max_score": 5,
                "difficulty_level": "medium"
            }
        ]
    
    def generate_mcq(self, topic: str, explanation: str, difficulty: str, question_num: int) -> Dict:
        """Generate multiple choice question"""
        prompt = f"""
        Generate a multiple-choice question about: {topic}
        
        Based on this explanation:
        {explanation[:1000]}
        
        Difficulty: {difficulty}
        
        Requirements:
        1. Question should test conceptual understanding
        2. Include 4 options (A, B, C, D)
        3. Only one correct answer
        4. Include plausible distractors (common misconceptions)
        5. Provide explanation for the correct answer
        
        Format JSON:
        {{
            "id": {question_num},
            "type": "mcq",
            "question": "question text here",
            "options": {{
                "A": "option A",
                "B": "option B", 
                "C": "option C",
                "D": "option D"
            }},
            "correct_answer": "A/B/C/D",
            "explanation": "detailed explanation of correct answer",
            "difficulty_level": "easy/medium/hard",
            "concepts_tested": ["concept1", "concept2"],
            "max_score": 2
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            question_data = json.loads(response.choices[0].message.content)
            question_data["max_score"] = 2  # Ensure max_score exists
            return question_data
        except Exception as e:
            logger.error(f"MCQ generation error: {str(e)}")
            return None
    
    def generate_short_answer(self, topic: str, explanation: str, difficulty: str, question_num: int) -> Dict:
        """Generate short answer question"""
        prompt = f"""
        Generate a short-answer question about: {topic}
        
        Based on this explanation:
        {explanation[:1000]}
        
        Difficulty: {difficulty}
        
        Requirements:
        1. Question requiring 2-3 sentence answer
        2. Provide model answer and key points
        3. Include grading rubric
        
        Format JSON:
        {{
            "id": {question_num},
            "type": "short_answer",
            "question": "question text here",
            "model_answer": "ideal answer here",
            "key_points": ["point1", "point2", "point3"],
            "rubric": {{
                "excellent": "criteria for full marks",
                "good": "criteria for partial marks",
                "poor": "criteria for low marks"
            }},
            "max_score": 5,
            "difficulty_level": "easy/medium/hard"
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Short answer generation error: {str(e)}")
            return None
    
    def generate_code_completion(self, topic: str, explanation: str, difficulty: str, question_num: int) -> Dict:
        """Generate code completion question"""
        prompt = f"""
        Generate a Python code completion question about: {topic}
        
        Based on this explanation:
        {explanation[:1000]}
        
        Difficulty: {difficulty}
        
        Requirements:
        1. Provide incomplete Python code with missing parts
        2. Test specific programming concept
        3. Include expected output
        4. Provide solution code
        
        Format JSON:
        {{
            "id": {question_num},
            "type": "code_completion",
            "question": "question description",
            "incomplete_code": "def function_name():\n    # TODO: Complete this function\n    pass",
            "expected_output": "expected output description",
            "solution": "complete solution code",
            "hints": ["hint1", "hint2"],
            "max_score": 10,
            "concepts_tested": ["concept1", "concept2"]
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Code completion generation error: {str(e)}")
            return None
    
    def generate_true_false(self, topic: str, explanation: str, difficulty: str, question_num: int) -> Dict:
        """Generate true/false question with justification"""
        prompt = f"""
        Generate a true/false question about: {topic}
        
        Based on this explanation:
        {explanation[:1000]}
        
        Difficulty: {difficulty}
        
        Requirements:
        1. Statement that is either true or false
        2. Include justification for why it's true/false
        3. Test common misconceptions
        
        Format JSON:
        {{
            "id": {question_num},
            "type": "true_false",
            "statement": "statement here",
            "correct_answer": true/false,
            "justification": "detailed justification",
            "common_misconception": "common wrong belief",
            "max_score": 2
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"True/false generation error: {str(e)}")
            return None
    
    def generate_fill_blanks(self, topic: str, explanation: str, difficulty: str, question_num: int) -> Dict:
        """Generate fill-in-the-blanks question"""
        prompt = f"""
        Generate a fill-in-the-blanks question about: {topic}
        
        Based on this explanation:
        {explanation[:1000]}
        
        Difficulty: {difficulty}
        
        Requirements:
        1. Paragraph with 3-5 blanks
        2. Word bank or specific answers
        3. Answer key
        
        Format JSON:
        {{
            "id": {question_num},
            "type": "fill_blanks",
            "text": "paragraph with _____ blanks",
            "blanks": [
                {{"position": 1, "correct_answer": "answer1", "hint": "hint1"}},
                {{"position": 2, "correct_answer": "answer2", "hint": "hint2"}}
            ],
            "max_score": 5
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Fill blanks generation error: {str(e)}")
            return None
    
    def generate_numerical_problem(self, topic: str, explanation: str, difficulty: str, question_num: int) -> Dict:
        """Generate numerical problem solving question"""
        prompt = f"""
        Generate a numerical problem about: {topic}
        
        Based on this explanation:
        {explanation[:1000]}
        
        Difficulty: {difficulty}
        
        Requirements:
        1. Problem statement with numbers
        2. Step-by-step solution
        3. Final answer
        
        Format JSON:
        {{
            "id": {question_num},
            "type": "numerical_problem",
            "problem": "problem statement with numbers",
            "steps": [
                {{"step": 1, "description": "step description"}},
                {{"step": 2, "description": "step description"}}
            ],
            "correct_answer": "final numerical answer",
            "formula": "mathematical formula if applicable",
            "max_score": 10
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Numerical problem generation error: {str(e)}")
            return None

class QuizEvaluator:
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def evaluate_answers(self, quiz: Dict, student_answers: Dict, student_email: str) -> Dict:
        total_score = 0
        max_score = 0
        question_results = []
        
        for question in quiz["questions"]:
            q_id = question["id"]
            student_answer = student_answers.get(str(q_id), "")
            
            if question["type"] == "mcq":
                result = self.evaluate_mcq(question, student_answer)
            elif question["type"] == "short_answer":
                result = self.evaluate_short_answer(question, student_answer)
            elif question["type"] == "code_completion":
                result = self.evaluate_code_completion(question, student_answer)
            elif question["type"] == "true_false":
                result = self.evaluate_true_false(question, student_answer)
            elif question["type"] == "fill_blanks":
                result = self.evaluate_fill_blanks(question, student_answer)
            elif question["type"] == "numerical_problem":
                result = self.evaluate_numerical_problem(question, student_answer)
            else:
                result = {
                    "score": 0,
                    "max_score": question.get("max_score", 5),
                    "feedback": "Question type not supported"
                }
            
            total_score += result["score"]
            max_score += result["max_score"]
            
            question_results.append({
                "question_id": q_id,
                "question_type": question["type"],
                "question_text": question.get("question", question.get("statement", "")),
                "student_answer": student_answer,
                "score": result["score"],
                "max_score": result["max_score"],
                "feedback": result["feedback"]
            })
        
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        assessment = self.generate_personalized_assessment(
            quiz["topic"],
            question_results,
            percentage,
            student_email
        )
        
        return {
            "student_email": student_email,
            "topic": quiz["topic"],
            "total_score": total_score,
            "max_score": max_score,
            "percentage": percentage,
            "grade": self.calculate_grade(percentage),
            "question_results": question_results,
            "assessment": assessment,
            "evaluated_at": datetime.now().isoformat()
        }
    
    def evaluate_mcq(self, question: Dict, student_answer: str) -> Dict:
        """Evaluate multiple choice answer"""
        correct = question.get("correct_answer", "A")
        is_correct = student_answer.upper() == correct.upper()
        
        score = question.get("max_score", 2) if is_correct else 0
        
        return {
            "score": score,
            "max_score": question.get("max_score", 2),
            "feedback": f"{'Correct!' if is_correct else 'Incorrect.'} {question.get('explanation', '')}"
        }
    
    def evaluate_short_answer(self, question: Dict, student_answer: str) -> Dict:
        """Evaluate short answer using LLM"""
        prompt = f"""
        Evaluate this short answer:
        
        Question: {question["question"]}
        Model Answer: {question["model_answer"]}
        Key Points: {', '.join(question.get('key_points', []))}
        
        Student Answer: {student_answer}
        
        Rubric:
        Excellent ({question.get('max_score', 5)} points): {question['rubric']['excellent']}
        Good ({question.get('max_score', 5) * 0.7} points): {question['rubric']['good']}
        Poor ({question.get('max_score', 5) * 0.3} points): {question['rubric']['poor']}
        
        Score on scale of 0 to {question.get('max_score', 5)}.
        Provide specific feedback and suggestions for improvement.
        
        Return JSON:
        {{
            "score": <number>,
            "feedback": "<detailed feedback>"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            score = float(result["score"])
            return {
                "score": min(score, question.get("max_score", 5)),
                "max_score": question.get("max_score", 5),
                "feedback": result["feedback"]
            }
        except:

            student_lower = student_answer.lower()
            model_lower = question["model_answer"].lower()
            

            key_points = question.get("key_points", [])
            matches = sum(1 for point in key_points if point.lower() in student_lower)
            score = (matches / len(key_points)) * question.get("max_score", 5) if key_points else 0
            
            return {
                "score": score,
                "max_score": question.get("max_score", 5),
                "feedback": f"Score based on keyword matching: {score:.1f}/{question.get('max_score', 5)}"
            }
    
    def evaluate_code_completion(self, question: Dict, student_answer: str) -> Dict:
        """Evaluate code completion answer"""
        solution = question.get("solution", "").lower()
        student_code = student_answer.lower()
        
        solution_keywords = re.findall(r'def (\w+)|import (\w+)|from (\w+)|class (\w+)', solution)
        solution_keywords = [kw for group in solution_keywords for kw in group if kw]
        
        matches = sum(1 for kw in solution_keywords if kw in student_code)
        score = 0
        
        if matches > 0:
            score = (matches / max(len(solution_keywords), 1)) * question.get("max_score", 10)
        
        return {
            "score": min(score, question.get("max_score", 10)),
            "max_score": question.get("max_score", 10),
            "feedback": f"Code completion scored: {score:.1f}/{question.get('max_score', 10)}. "
                       f"Check if your solution produces the expected output."
        }
    
    def evaluate_true_false(self, question: Dict, student_answer: str) -> Dict:
        try:
            student_bool = student_answer.lower() in ["true", "t", "yes", "y", "1"]
            correct_bool = question.get("correct_answer", True)
            
            is_correct = student_bool == correct_bool
            score = question.get("max_score", 2) if is_correct else 0
            
            return {
                "score": score,
                "max_score": question.get("max_score", 2),
                "feedback": f"{'Correct!' if is_correct else 'Incorrect.'} {question.get('justification', '')}"
            }
        except:
            return {
                "score": 0,
                "max_score": question.get("max_score", 2),
                "feedback": "Invalid answer format. Expected 'true' or 'false'."
            }
    
    def evaluate_fill_blanks(self, question: Dict, student_answer: str) -> Dict:
        """Evaluate fill-in-the-blanks answer"""
        try:
            if isinstance(student_answer, str):
                student_answers = [ans.strip() for ans in student_answer.split(",")]
            else:
                student_answers = student_answer
            
            blanks = question.get("blanks", [])
            correct_count = 0
            
            for i, blank in enumerate(blanks):
                if i < len(student_answers):
                    student_ans = student_answers[i].lower().strip()
                    correct_ans = blank.get("correct_answer", "").lower().strip()
                    if student_ans == correct_ans:
                        correct_count += 1
            
            score = (correct_count / len(blanks)) * question.get("max_score", 5) if blanks else 0
            
            return {
                "score": score,
                "max_score": question.get("max_score", 5),
                "feedback": f"{correct_count}/{len(blanks)} blanks correct."
            }
        except:
            return {
                "score": 0,
                "max_score": question.get("max_score", 5),
                "feedback": "Error evaluating fill-in-the-blanks."
            }
    
    def evaluate_numerical_problem(self, question: Dict, student_answer: str) -> Dict:
        """Evaluate numerical problem answer"""
        try:
            student_num = float(student_answer)
            correct_num = float(question.get("correct_answer", 0))
            
            tolerance = 0.01
            is_correct = abs(student_num - correct_num) <= tolerance
            
            score = question.get("max_score", 10) if is_correct else 0
            
            return {
                "score": score,
                "max_score": question.get("max_score", 10),
                "feedback": f"{'Correct!' if is_correct else 'Incorrect. Expected: ' + str(correct_num)}"
            }
        except:
            student_clean = str(student_answer).strip().lower()
            correct_clean = str(question.get("correct_answer", "")).strip().lower()
            
            is_correct = student_clean == correct_clean
            score = question.get("max_score", 10) if is_correct else 0
            
            return {
                "score": score,
                "max_score": question.get("max_score", 10),
                "feedback": f"{'Correct!' if is_correct else 'Incorrect.'}"
            }
    
    def calculate_grade(self, percentage: float) -> str:
        """Calculate letter grade"""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
    def _generate_basic_assessment(self, topic: str, performance_data: List, percentage: float) -> Dict:
        """Generate basic assessment when LLM fails"""
        # Simple analysis based on performance data
        strengths = []
        weaknesses = []
        
        for perf in performance_data:
            # Ensure perf is a dictionary
            if isinstance(perf, dict):
                score = float(perf.get("score", 0))
                max_score = float(perf.get("max_score", 1))
                score_ratio = score / max_score if max_score > 0 else 0
                question_type = str(perf.get("question_type", "unknown"))
                
                if score_ratio >= 0.7:
                    strengths.append(f"{question_type.replace('_', ' ').title()} questions")
                else:
                    weaknesses.append(f"{question_type.replace('_', ' ').title()} questions")
        
        # Determine mastery level
        if percentage >= 85:
            mastery = "Advanced"
            next_steps = "Explore advanced applications and research papers"
        elif percentage >= 70:
            mastery = "Intermediate"
            next_steps = "Practice complex problems and real-world applications"
        else:
            mastery = "Beginner"
            next_steps = "Review fundamentals and basic concepts"
        
        return {
            "topic": topic,
            "mastery_level": mastery,
            "mastery_explanation": f"Based on your score of {percentage:.1f}%",
            "percentage": percentage,
            "grade": self.calculate_grade(percentage),
            "strengths": [{"area": s, "evidence": "Performed well on these questions", "explanation": ""} for s in strengths[:3]],
            "weaknesses": [{"area": w, "evidence": "Needs improvement in these areas", "explanation": "", "correct_concept": ""} for w in weaknesses[:3]],
            "personalized_recommendations": [
                f"Review {topic} fundamentals",
                "Practice more questions of types you struggled with",
                "Seek additional learning resources"
            ],
            "learning_roadmap": self._generate_basic_roadmap(topic, weaknesses, mastery),
            "specific_resources": [
                {
                    "type": "book",
                    "title": f"Introduction to {topic}",
                    "url": "#",
                    "reason": "Covers fundamental concepts"
                }
            ],
            "encouragement": {
                "positive_feedback": "Keep up the good work!",
                "motivational_message": "Continuous learning leads to mastery.",
                "improvement_goal": f"Aim for {(percentage + 10):.1f}% on your next attempt"
            }
        }
    
    def generate_personalized_assessment(self, topic: str, question_results: List, percentage: float, student_email: str) -> Dict:
        """Generate truly personalized assessment using LLM analysis"""
        
        # Prepare detailed performance data for LLM analysis
        performance_data = []
        for result in question_results:
            # Ensure all values are properly formatted
            student_answer = str(result.get("student_answer", ""))
            question_text = str(result.get("question_text", ""))
            feedback = str(result.get("feedback", ""))
            
            performance_data.append({
                "question_type": result.get("question_type", "unknown"),
                "question_text": question_text[:200] + "..." if len(question_text) > 200 else question_text,
                "student_answer": student_answer[:200] + "..." if len(student_answer) > 200 else student_answer,
                "score": float(result.get("score", 0)),
                "max_score": float(result.get("max_score", 1)),
                "feedback": feedback[:200] + "..." if len(feedback) > 200 else feedback
            })
        
        # Use LLM to analyze performance and generate personalized assessment
        personalized_analysis = self._analyze_performance_with_llm(
            topic=topic,
            performance_data=performance_data,
            percentage=percentage,
            student_email=student_email
        )
        
        return personalized_analysis
    
    def _analyze_performance_with_llm(self, topic: str, performance_data: List, percentage: float, student_email: str) -> Dict:
        """Use LLM to analyze student performance and generate personalized assessment"""
        
        # Convert performance data to safe JSON string
        perf_json = json.dumps(performance_data, indent=2, ensure_ascii=False)
        
        prompt = f"""
        Analyze this student's quiz performance and create a personalized learning assessment.
        
        STUDENT INFORMATION:
        - Topic: {topic}
        - Overall Score: {percentage:.1f}%
        - Email: {student_email}
        
        PERFORMANCE DETAILS:
        {perf_json}
        
        GRADE CALCULATION:
        - A: 90-100%, B: 80-89%, C: 70-79%, D: 60-69%, F: Below 60%
        - Current Grade: {self.calculate_grade(percentage)}
        
        TASK: Create a detailed, personalized assessment including:
        
        1. MASTERY LEVEL ASSESSMENT:
           - Determine if student is Beginner, Intermediate, or Advanced
           - Explain why based on their specific performance
        
        2. STRENGTHS ANALYSIS:
           - Identify 2-3 specific strengths based on their answers
           - Quote specific answers that demonstrate understanding
           - Explain why these are strengths
        
        3. WEAKNESSES ANALYSIS:
           - Identify 2-3 specific weaknesses based on their answers
           - Quote specific answers that show misconceptions
           - Explain the underlying knowledge gaps
        
        4. PERSONALIZED RECOMMENDATIONS:
           - 3-5 specific actions they should take
           - Tailor recommendations to their actual mistakes
           - Include both conceptual review and practical practice
        
        5. PERSONALIZED ROADMAP (4-week plan):
           - Week 1: Address specific weaknesses from this quiz
           - Week 2: Build on identified strengths
           - Week 3: Practical application based on their performance
           - Week 4: Advanced topics or projects based on their level
        
        6. SPECIFIC RESOURCES:
           - Recommend specific resources based on their weaknesses
           - Include books, videos, courses, practice sites
        
        7. ENCOURAGEMENT AND MOTIVATION:
           - Provide specific encouragement based on their performance
           - Acknowledge what they did well
           - Motivate them to improve specific areas
        
        Return ONLY JSON with this structure:
        {{
            "topic": "{topic}",
            "mastery_level": "Beginner/Intermediate/Advanced",
            "mastery_explanation": "detailed explanation",
            "percentage": {percentage},
            "grade": "{self.calculate_grade(percentage)}",
            "strengths": [
                {{
                    "area": "specific strength area",
                    "evidence": "quote from their answer",
                    "explanation": "why this is a strength"
                }}
            ],
            "weaknesses": [
                {{
                    "area": "specific weakness area",
                    "evidence": "quote from their answer",
                    "explanation": "underlying misconception",
                    "correct_concept": "what they should understand"
                }}
            ],
            "personalized_recommendations": [
                "specific action 1",
                "specific action 2",
                "specific action 3"
            ],
            "learning_roadmap": [
                {{
                    "week": 1,
                    "focus": "specific focus based on weaknesses",
                    "activities": ["activity 1", "activity 2"],
                    "resources": ["resource 1", "resource 2"],
                    "expected_outcome": "what they should achieve"
                }},
                {{
                    "week": 2,
                    "focus": "building on strengths",
                    "activities": ["activity 1", "activity 2"],
                    "resources": ["resource 1", "resource 2"],
                    "expected_outcome": "what they should achieve"
                }},
                {{
                    "week": 3,
                    "focus": "practical application",
                    "activities": ["activity 1", "activity 2"],
                    "resources": ["resource 1", "resource 2"],
                    "expected_outcome": "what they should achieve"
                }},
                {{
                    "week": 4,
                    "focus": "advanced topics/projects",
                    "activities": ["activity 1", "activity 2"],
                    "resources": ["resource 1", "resource 2"],
                    "expected_outcome": "what they should achieve"
                }}
            ],
            "specific_resources": [
                {{
                    "type": "book/video/course",
                    "title": "resource title",
                    "url": "resource url if available",
                    "reason": "why this resource helps their specific weakness"
                }}
            ],
            "encouragement": {{
                "positive_feedback": "specific positive feedback",
                "motivational_message": "personalized motivational message",
                "improvement_goal": "specific goal for next assessment"
            }}
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            assessment_text = response.choices[0].message.content
            logger.info(f"LLM assessment generated: {len(assessment_text)} chars")
            
            assessment = json.loads(assessment_text)
            
            # Add any missing fields with safe defaults
            assessment["topic"] = topic
            assessment["percentage"] = percentage
            assessment["grade"] = self.calculate_grade(percentage)
            
            # Ensure all lists exist
            assessment.setdefault("strengths", [])
            assessment.setdefault("weaknesses", [])
            assessment.setdefault("personalized_recommendations", [])
            assessment.setdefault("learning_roadmap", [])
            assessment.setdefault("specific_resources", [])
            assessment.setdefault("encouragement", {})
            
            # Ensure encouragement has all fields
            encouragement = assessment["encouragement"]
            encouragement.setdefault("positive_feedback", "Good work on attempting the quiz!")
            encouragement.setdefault("motivational_message", "Every learning journey begins with a single step.")
            encouragement.setdefault("improvement_goal", f"Aim for {percentage + 10:.1f}% on your next attempt")
            
            return assessment
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in assessment: {str(e)}")
            logger.error(f"Response received: {assessment_text[:500]}")
            return self._generate_basic_assessment(topic, performance_data, percentage)
        except Exception as e:
            logger.error(f"LLM assessment generation error: {str(e)}")
            return self._generate_basic_assessment(topic, performance_data, percentage)
    
    def generate_roadmap(self, topic: str, weaknesses: List, mastery: str) -> List[Dict]:
        """Generate personalized learning roadmap"""
        roadmap = []
 
        roadmap.append({
            "week": 1,
            "focus": "Fundamentals Review",
            "activities": [
                "Review basic concepts of " + topic,
                "Watch introductory videos",
                "Complete practice exercises"
            ],
            "resources": [
                "Khan Academy",
                "Coursera introductory courses",
                "YouTube tutorials"
            ]
        })
        
        roadmap.append({
            "week": 2,
            "focus": "Skill Building",
            "activities": [
                "Work on " + ", ".join(weaknesses[:2]) if weaknesses else "Practice problems",
                "Join study groups",
                "Attempt mini-projects"
            ],
            "resources": [
                "Practice websites (LeetCode, HackerRank for technical topics)",
                "Online forums (Stack Overflow, Reddit)",
                "Textbook exercises"
            ]
        })
        
        roadmap.append({
            "week": "3-4",
            "focus": "Real-world Application",
            "activities": [
                "Complete a capstone project on " + topic,
                "Analyze case studies",
                "Participate in peer reviews"
            ],
            "resources": [
                "GitHub repositories",
                "Research papers",
                "Industry case studies"
            ]
        })
        
        return roadmap

def send_assessment_email(student_email: str, assessment: Dict, quiz_result: Dict):
    """Generate and send personalized assessment email (safe version without f‑string backslashes)"""
    from agents.email_agent import send_notification

    topic = assessment.get('topic', quiz_result.get('topic', 'Learning Assessment'))
    subject = f"📚 Your Personalized Learning Assessment: {topic}"

    # Build strengths section
    strengths_html = ""
    if assessment.get('strengths'):
        strengths_html = "<h3 style='color: #2E7D32;'>✅ Your Strengths:</h3>"
        for strength in assessment['strengths'][:3]:
            area = strength.get('area', '')
            evidence = strength.get('evidence', '')
            explanation = strength.get('explanation', '')
            strengths_html += f"""
            <div style='background: #E8F5E9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50;'>
                <h4 style='margin-top: 0;'>🎯 {area}</h4>
                {f"<p><strong>Evidence:</strong> <em>“{evidence}”</em></p>" if evidence else ""}
                <p>{explanation}</p>
            </div>
            """
    else:
        strengths_html = "<p>No significant strengths identified yet. Keep practicing!</p>"

    # Build weaknesses section
    weaknesses_html = ""
    if assessment.get('weaknesses'):
        weaknesses_html = "<h3 style='color: #C62828;'>📝 Areas for Improvement:</h3>"
        for weakness in assessment['weaknesses'][:3]:
            area = weakness.get('area', '')
            evidence = weakness.get('evidence', '')
            explanation = weakness.get('explanation', '')
            correct_concept = weakness.get('correct_concept', '')
            weaknesses_html += f"""
            <div style='background: #FFEBEE; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #F44336;'>
                <h4 style='margin-top: 0;'>🔧 {area}</h4>
                {f"<p><strong>Your answer:</strong> <em>“{evidence}”</em></p>" if evidence else ""}
                {f"<p><strong>Issue:</strong> {explanation}</p>" if explanation else ""}
                {f"<p><strong>Correct understanding:</strong> {correct_concept}</p>" if correct_concept else ""}
            </div>
            """
    else:
        weaknesses_html = "<p>Great job! No major weaknesses identified.</p>"

    # Personalized recommendations
    recommendations_html = ""
    if assessment.get('personalized_recommendations'):
        recs = assessment['personalized_recommendations'][:5]
        items = "".join(f"<li style='margin-bottom: 10px;'><strong>{i+1}.</strong> {rec}</li>" for i, rec in enumerate(recs))
        recommendations_html = f"<h3 style='color: #1565C0;'>🎯 Personalized Recommendations:</h3><ul style='background: #E3F2FD; padding: 20px; border-radius: 5px;'>{items}</ul>"

    # Learning roadmap
    roadmap_html = ""
    if assessment.get('learning_roadmap'):
        roadmap_html = "<h3 style='color: #6A1B9A;'>🗺️ Your Personalized Learning Roadmap:</h3>"
        for step in assessment['learning_roadmap']:
            activities = "".join(f"<li>{activity}</li>" for activity in step.get('activities', []))
            roadmap_html += f"""
            <div style='background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); 
                        padding: 20px; margin: 15px 0; border-radius: 8px; border: 1px solid #ddd;'>
                <h4 style='color: #6A1B9A; margin-top: 0;'>📅 Week {step['week']}: {step['focus']}</h4>
                <p><strong>🎯 Expected Outcome:</strong> {step.get('expected_outcome', 'Improved understanding')}</p>
                <p><strong>📝 Activities:</strong></p>
                <ul>{activities}</ul>
                <p><strong>📚 Resources:</strong> {', '.join(step.get('resources', []))}</p>
            </div>
            """

    # Specific resources
    resources_html = ""
    if assessment.get('specific_resources'):
        resources_html = "<h3 style='color: #00838F;'>📖 Recommended Resources:</h3>"
        for resource in assessment['specific_resources'][:5]:
            rtype = resource.get('type', 'Resource').title()
            title = resource.get('title', '')
            url = resource.get('url', '#')
            reason = resource.get('reason', '')
            resources_html += f"""
            <div style='background: #E0F7FA; padding: 15px; margin: 10px 0; border-radius: 5px;'>
                <p><strong>{rtype}:</strong> {title}</p>
                {f'<p><strong>Why:</strong> {reason}</p>' if reason else ''}
                {f'<p><a href="{url}" style="color: #006064; text-decoration: none;">🔗 Access Resource</a></p>' if url != '#' else ''}
            </div>
            """

    encouragement = assessment.get('encouragement', {})
    positive_feedback = encouragement.get('positive_feedback', 'Good work!')
    motivational_message = encouragement.get('motivational_message', 'Keep learning!')
    improvement_goal = encouragement.get('improvement_goal', 'Improve your score next time')

    mastery_html = ""
    if assessment.get('mastery_explanation'):
        mastery_level = assessment.get('mastery_level', 'Not Assessed')
        mastery_color = '#4CAF50' if mastery_level == 'Advanced' else '#FF9800' if mastery_level == 'Intermediate' else '#F44336'
        mastery_html = f"""
        <div style='background: {mastery_color}20; padding: 15px; border-radius: 5px; border-left: 4px solid {mastery_color}; margin: 20px 0;'>
            <h4 style='color: {mastery_color}; margin-top: 0;'>🎓 Mastery Level: {mastery_level}</h4>
            <p>{assessment['mastery_explanation']}</p>
        </div>
        """

    # Final HTML – no backslashes inside f‑string expressions (all backslashes are outside {})
    body_html = f"""
    <html>
    <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>
        <div style='max-width: 800px; margin: 0 auto; padding: 20px;'>
            <div style='text-align: center; margin-bottom: 30px;'>
                <h1 style='color: #2c3e50; margin-bottom: 10px;'>📚 Personalized Learning Assessment</h1>
                <p style='color: #7f8c8d;'>Your customized learning journey for <strong>{topic}</strong></p>
            </div>
            
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 25px; border-radius: 10px; margin: 20px 0;'>
                <h2 style='margin-top: 0;'>Assessment Summary</h2>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;'>
                    <div>
                        <p><strong>📖 Topic:</strong> {topic}</p>
                        <p><strong>📊 Overall Score:</strong> {quiz_result.get('percentage', 0):.1f}%</p>
                    </div>
                    <div>
                        <p><strong>🎯 Grade:</strong> {assessment.get('grade', 'N/A')}</p>
                        <p><strong>📈 Mastery Level:</strong> {assessment.get('mastery_level', 'Not Assessed')}</p>
                    </div>
                </div>
            </div>
            
            {mastery_html}
            
            <div style='display: grid; grid-template-columns: 1fr; gap: 25px; margin: 30px 0;'>
                <div>{strengths_html}</div>
                <div>{weaknesses_html}</div>
            </div>
            
            {recommendations_html}
            {roadmap_html}
            {resources_html}
            
            <div style='margin-top: 30px; padding: 20px; background: #FFF3E0; border-radius: 5px; border-left: 4px solid #FF9800;'>
                <h3 style='color: #EF6C00;'>💪 Encouragement & Motivation</h3>
                <p><strong>Positive Feedback:</strong> {positive_feedback}</p>
                <p><strong>Motivational Message:</strong> {motivational_message}</p>
                <p><strong>Next Goal:</strong> {improvement_goal}</p>
            </div>
            
            <div style='margin-top: 30px; padding: 15px; background: #f5f5f5; border-radius: 5px;'>
                <h3>Detailed Performance:</h3>
                <p>Total Score: {quiz_result.get('total_score', 0)}/{quiz_result.get('max_score', 0)}</p>
                <p>Assessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Student Email: {student_email}</p>
            </div>
            
            <hr style='margin: 30px 0; border: none; border-top: 2px dashed #ddd;'>
            
            <div style='text-align: center; color: #666; font-size: 0.9em;'>
                <p>This personalized assessment was generated by your AI Learning System.</p>
                <p>Your learning journey is unique - progress at your own pace! 🌱</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_notification(subject, body_html, to_email=student_email)
