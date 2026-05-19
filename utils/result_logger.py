import json
import os
import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any
import logging
import seaborn as sns
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

class ResultLogger:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir="results"):
        if not hasattr(self, 'initialized'):
            self.log_dir = log_dir
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_log = []
            self.llm_responses = []
            self.rag_results = []
            self.quiz_results = []
            self.assessments = []
            self.evaluations = []
            self.web_content = []
            
            # Create results directory
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Setup logging
            self.setup_logging()
            self.initialized = True
    
    def setup_logging(self):
        """Setup file logging for detailed results"""
        self.log_file = os.path.join(self.log_dir, f"session_{self.session_id}.txt")
        self.csv_file = os.path.join(self.log_dir, f"session_{self.session_id}.csv")
        
        # Create header
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"PERSONALIZED LEARNING SYSTEM - SESSION LOG\n")
            f.write(f"Session ID: {self.session_id}\n")
            f.write(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
    
    def log_query(self, query: str, routing_info: Dict):
        """Log user query and routing information"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "query",
            "query": query,
            "routing_info": routing_info
        }
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_rag_retrieval(self, module: int, topic: str, results: List):
        """Log RAG retrieval results"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "rag_retrieval",
            "module": module,
            "topic": topic,
            "num_results": len(results),
            "results": results,
            "scores": [r['score'] for r in results] if results else []
        }
        self.rag_results.append(entry)
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_llm_response(self, model: str, prompt: str, response: str, tokens: int = None):
        """Log individual LLM response"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "llm_response",
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "response_preview": response[:500] + "..." if len(response) > 500 else response
        }
        self.llm_responses.append(entry)
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_all_llm_responses(self, query: str, responses: List[Dict]):
        """Log all LLM responses before selection"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "all_llm_responses",
            "query": query,
            "responses": []
        }
        
        for i, resp_data in enumerate(responses):
            if isinstance(resp_data, dict):
                model = resp_data.get('model', f'Model_{i}')
                content = resp_data.get('content', '')
            else:
                model = f'Model_{i}'
                content = str(resp_data) if resp_data else ''
            
            entry["responses"].append({
                "model": model,
                "content_length": len(content),
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "full_content": content  # Store full content
            })
        
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_llm_comparison(self, query: str, responses: List[Dict], selected: Dict):
        """Log comparison of multiple LLM responses"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "llm_comparison",
            "query": query,
            "responses": [
                {
                    "model": resp.get('model', 'unknown'),
                    "content_length": len(resp.get('content', '')),
                    "selected": resp.get('model') == selected.get('model')
                }
                for resp in responses
            ],
            "selected_model": selected.get('model'),
            "selection_score": selected.get('score', 0)
        }
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_evaluation(self, criteria_scores: Dict, evaluator_model: str, response_index: int, 
                      response_model: str = None, weighted_score: float = None, 
                      is_self_evaluation: bool = False):
        """Log peer review evaluation scores with complete details"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "evaluation",
            "evaluator_model": evaluator_model,
            "response_index": response_index,
            "response_model": response_model if response_model else f"Response_{response_index}",
            "criteria_scores": criteria_scores,
            "weighted_score": weighted_score if weighted_score is not None else sum(criteria_scores.values()) / len(criteria_scores) if criteria_scores else 0,
            "is_self_evaluation": is_self_evaluation,
            "evaluation_matrix_position": f"{evaluator_model}->Response_{response_index}"
        }
        self.evaluations.append(entry)
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_web_content(self, agent_type: str, topic: str, results: List):
        """Log web agent results"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": f"web_{agent_type}",
            "topic": topic,
            "num_results": len(results),
            "results": results
        }
        self.web_content.append(entry)
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_quiz_generation(self, topic: str, quiz: Dict):
        """Log quiz generation"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "quiz_generation",
            "topic": topic,
            "num_questions": len(quiz.get('questions', [])),
            "question_types": [q['type'] for q in quiz.get('questions', [])],
            "difficulty": quiz.get('difficulty', 'medium')
        }
        self.quiz_results.append(entry)
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_quiz_evaluation(self, quiz_result: Dict, assessment: Dict):
        """Log quiz evaluation results"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "quiz_evaluation",
            "topic": quiz_result.get('topic'),
            "total_score": quiz_result.get('total_score'),
            "max_score": quiz_result.get('max_score'),
            "percentage": quiz_result.get('percentage'),
            "grade": quiz_result.get('grade'),
            "mastery_level": assessment.get('mastery_level'),
            "strengths": assessment.get('strengths', []),
            "weaknesses": assessment.get('weaknesses', [])
        }
        self.assessments.append(entry)
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def log_final_response(self, response: Dict):
        """Log final system response"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "final_response",
            "status": response.get('status'),
            "topic": response.get('topic'),
            "module": response.get('module'),
            "learning_style": response.get('learning_style'),
            "llm_used": response.get('llm_used'),
            "explanation_length": len(response.get('explanation', '')),
            "num_sources": len(response.get('sources', []))
        }
        self.session_log.append(entry)
        self._write_entry(entry)
    
    def _write_entry(self, entry: Dict):
        """Write entry to log file"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TYPE: {entry['type'].upper()}\n")
            f.write(f"TIME: {entry['timestamp']}\n")
            f.write(f"{'='*60}\n")
            
            if entry['type'] == 'query':
                f.write(f"QUERY: {entry['query']}\n")
                f.write(f"ROUTING: Module={entry['routing_info'].get('module')}, "
                       f"Style={entry['routing_info'].get('style')}, "
                       f"InDomain={entry['routing_info'].get('in_domain')}\n")
            
            elif entry['type'] == 'rag_retrieval':
                f.write(f"TOPIC: {entry['topic']}\n")
                f.write(f"MODULE: {entry['module']}\n")
                f.write(f"RETRIEVED: {entry['num_results']} chunks\n")
                if entry['scores']:
                    f.write(f"SCORES: Min={min(entry['scores']):.3f}, "
                           f"Max={max(entry['scores']):.3f}, "
                           f"Avg={np.mean(entry['scores']):.3f}\n")
            
            elif entry['type'] == 'llm_response':
                f.write(f"MODEL: {entry['model']}\n")
                f.write(f"PROMPT LENGTH: {entry['prompt_length']} chars\n")
                f.write(f"RESPONSE LENGTH: {entry['response_length']} chars\n")
                f.write(f"RESPONSE PREVIEW:\n{entry['response_preview']}\n")
            
            elif entry['type'] == 'all_llm_responses':
                f.write(f"QUERY: {entry['query']}\n")
                f.write(f"NUMBER OF RESPONSES: {len(entry['responses'])}\n")
                f.write("="*60 + "\n")
                
                for i, resp in enumerate(entry['responses']):
                    f.write(f"\nRESPONSE {i+1} - {resp['model']}:\n")
                    f.write(f"Length: {resp['content_length']} characters\n")
                    f.write("-"*40 + "\n")
                    
                    # Write full content with word wrapping
                    full_content = resp.get('full_content', '')
                    if full_content:
                        # Write in chunks to avoid extremely long lines
                        lines = full_content.split('\n')
                        for line in lines:
                            if len(line) > 100:
                                # Wrap long lines
                                chunks = [line[j:j+100] for j in range(0, len(line), 100)]
                                for chunk in chunks:
                                    f.write(chunk + "\n")
                            else:
                                f.write(line + "\n")
                    else:
                        f.write(f"Preview: {resp['content_preview']}\n")
                    
                    f.write("-"*40 + "\n")
            
            elif entry['type'] == 'llm_comparison':
                f.write(f"QUERY: {entry['query']}\n")
                f.write("RESPONSES:\n")
                for resp in entry['responses']:
                    f.write(f"  - {resp['model']}: {resp['content_length']} chars "
                           f"{'(SELECTED)' if resp['selected'] else ''}\n")
                f.write(f"SELECTED: {entry['selected_model']}\n")
                f.write(f"SCORE: {entry.get('selection_score', 0):.3f}\n")
            
            elif entry['type'] == 'evaluation':
                f.write(f"EVALUATOR: {entry['evaluator_model']}\n")
                f.write(f"RESPONSE INDEX: {entry['response_index']}\n")
                f.write(f"RESPONSE MODEL: {entry.get('response_model', 'Unknown')}\n")
                f.write(f"EVALUATION MATRIX: {entry.get('evaluation_matrix_position', 'Unknown')}\n")
                f.write(f"IS SELF-EVALUATION: {entry.get('is_self_evaluation', False)}\n")
                f.write("CRITERIA SCORES:\n")
                for criterion, score in entry['criteria_scores'].items():
                    f.write(f"  - {criterion}: {score:.3f}\n")
                f.write(f"WEIGHTED SCORE: {entry['weighted_score']:.3f}\n")
            
            elif entry['type'].startswith('web_'):
                agent = entry['type'].replace('web_', '')
                f.write(f"AGENT: {agent}\n")
                f.write(f"TOPIC: {entry['topic']}\n")
                f.write(f"RESULTS: {entry['num_results']} items\n")
                for i, result in enumerate(entry['results'][:3]):
                    f.write(f"  {i+1}. {result.get('title', 'No title')}\n")
            
            elif entry['type'] == 'quiz_generation':
                f.write(f"TOPIC: {entry['topic']}\n")
                f.write(f"QUESTIONS: {entry['num_questions']}\n")
                f.write(f"TYPES: {', '.join(entry['question_types'])}\n")
                f.write(f"DIFFICULTY: {entry['difficulty']}\n")
            
            elif entry['type'] == 'quiz_evaluation':
                f.write(f"TOPIC: {entry['topic']}\n")
                f.write(f"SCORE: {entry['total_score']}/{entry['max_score']} "
                       f"({entry['percentage']:.1f}%)\n")
                f.write(f"GRADE: {entry['grade']}\n")
                f.write(f"MASTERY: {entry['mastery_level']}\n")
                f.write(f"STRENGTHS: {len(entry['strengths'])}\n")
                f.write(f"WEAKNESSES: {len(entry['weaknesses'])}\n")
            
            elif entry['type'] == 'final_response':
                f.write(f"STATUS: {entry['status']}\n")
                f.write(f"TOPIC: {entry['topic']}\n")
                f.write(f"MODULE: {entry['module']}\n")
                f.write(f"STYLE: {entry['learning_style']}\n")
                f.write(f"LLM: {entry['llm_used']}\n")
                f.write(f"EXPLANATION: {entry['explanation_length']} chars\n")
                f.write(f"SOURCES: {entry['num_sources']}\n")
    
    def generate_summary_statistics(self):
        """Generate comprehensive statistics"""
        stats = {
            "session_id": self.session_id,
            "total_queries": len([e for e in self.session_log if e['type'] == 'query']),
            "total_llm_responses": len(self.llm_responses),
            "total_rag_retrievals": len(self.rag_results),
            "total_quizzes": len(self.quiz_results),
            "total_assessments": len(self.assessments),
            "total_evaluations": len(self.evaluations),
            "start_time": self.session_log[0]['timestamp'] if self.session_log else None,
            "end_time": datetime.now().isoformat()
        }
        
        # LLM usage statistics
        if self.llm_responses:
            models = [r['model'] for r in self.llm_responses]
            stats['llm_models_used'] = list(set(models))
            stats['llm_response_counts'] = {model: models.count(model) for model in set(models)}
            stats['avg_response_length'] = np.mean([r['response_length'] for r in self.llm_responses])
        
        # RAG statistics
        if self.rag_results:
            scores = []
            for rag in self.rag_results:
                scores.extend(rag.get('scores', []))
            if scores:
                stats['rag_avg_score'] = np.mean(scores)
                stats['rag_min_score'] = min(scores)
                stats['rag_max_score'] = max(scores)
                stats['rag_std_score'] = np.std(scores)
        
        # Quiz statistics
        if self.assessments:
            percentages = [a['percentage'] for a in self.assessments]
            stats['quiz_avg_percentage'] = np.mean(percentages)
            stats['quiz_min_percentage'] = min(percentages)
            stats['quiz_max_percentage'] = max(percentages)
            stats['quiz_std_percentage'] = np.std(percentages)
        
        # Evaluation statistics
        if self.evaluations:
            weighted_scores = [e['weighted_score'] for e in self.evaluations]
            stats['eval_avg_score'] = np.mean(weighted_scores)
            stats['eval_min_score'] = min(weighted_scores)
            stats['eval_max_score'] = max(weighted_scores)
            stats['eval_std_score'] = np.std(weighted_scores)
        
        # Learning style distribution
        if self.session_log:
            styles = []
            for log in self.session_log:
                if log['type'] == 'query':
                    style = log['routing_info'].get('style')
                    if style:
                        styles.append(style)
            if styles:
                stats['learning_styles'] = {style: styles.count(style) for style in set(styles)}
        
        return stats
    
    def create_visualizations(self):
        """Create comprehensive visualizations for research analysis"""
        try:
            fig_dir = os.path.join(self.log_dir, "figures")
            os.makedirs(fig_dir, exist_ok=True)
            
            # Set style for publication-quality graphs
            plt.style.use('seaborn-v0_8-darkgrid')
            
            print("\n📊 Generating visualizations...")
            
            # 1. LLM PERFORMANCE COMPARISON (Bar Chart)
            if self.llm_responses:
                print("  Creating LLM performance charts...")
                self._create_llm_performance_chart(fig_dir)
            
            # 2. RAG RETRIEVAL ANALYSIS (Multiple Subplots)
            if self.rag_results:
                print("  Creating RAG analysis charts...")
                self._create_rag_analysis_charts(fig_dir)
            
            # 3. QUIZ PERFORMANCE DASHBOARD
            if self.assessments:
                print("  Creating quiz performance dashboard...")
                self._create_quiz_dashboard(fig_dir)
            
            # 4. PEER REVIEW EVALUATION HEATMAP
            if self.evaluations:
                print("  Creating evaluation heatmap...")
                self._create_evaluation_heatmap(fig_dir)
            
            # 5. SYSTEM PERFORMANCE TIMELINE
            if self.session_log:
                print("  Creating system timeline...")
                self._create_performance_timeline(fig_dir)
            
            # 6. LEARNING STYLE DISTRIBUTION
            if self.session_log:
                print("  Creating learning style chart...")
                self._create_learning_style_chart(fig_dir)
            
            # 7. MODEL SELECTION ANALYSIS
            if self.llm_responses and self.evaluations:
                print("  Creating model selection analysis...")
                self._create_model_selection_analysis(fig_dir)
            
            # 8. COMPREHENSIVE SYSTEM OVERVIEW
            print("  Creating system overview dashboard...")
            self._create_system_overview_dashboard(fig_dir)
            
            print(f"✅ Generated visualizations in {fig_dir}")
            
        except Exception as e:
            print(f"Error creating visualizations: {str(e)}")
            import traceback
            traceback.print_exc()

    def _create_llm_performance_chart(self, fig_dir):
        """Create comprehensive LLM performance comparison"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('LLM Performance Analysis', fontsize=16, fontweight='bold')
        
        # Data collection
        models_data = {}
        for resp in self.llm_responses:
            model = resp['model']
            if model not in models_data:
                models_data[model] = {'lengths': [], 'response_times': []}
        
        # Plot 1: Response Length Distribution
        lengths_data = []
        model_labels = []
        for model, data in models_data.items():
            model_responses = [r for r in self.llm_responses if r['model'] == model]
            lengths = [r['response_length'] for r in model_responses]
            lengths_data.append(lengths)
            model_labels.append(model)
        
        ax1.boxplot(lengths_data, labels=model_labels, patch_artist=True,
                   boxprops=dict(facecolor='lightblue', color='darkblue'),
                   medianprops=dict(color='red'))
        ax1.set_title('Response Length by Model', fontweight='bold')
        ax1.set_ylabel('Characters')
        ax1.grid(True, alpha=0.3)
        
        # Add mean markers
        for i, lengths in enumerate(lengths_data):
            if lengths:
                ax1.plot(i+1, np.mean(lengths), 'g_', markersize=15, label='Mean' if i == 0 else "")
        
        # Plot 2: Model Usage Frequency
        model_counts = {}
        for resp in self.llm_responses:
            model = resp['model']
            model_counts[model] = model_counts.get(model, 0) + 1
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(model_counts)))
        wedges, texts, autotexts = ax2.pie(model_counts.values(), labels=model_counts.keys(), 
                                          autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100.*sum(model_counts.values()))})',
                                          colors=colors, startangle=90, textprops={'fontsize': 10})
        ax2.set_title('Model Usage Distribution', fontweight='bold')
        
        # Plot 3: Selected vs Generated Counts
        selected_counts = {}
        generated_counts = {}
        
        # Count selections from comparison logs
        for log in self.session_log:
            if log['type'] == 'llm_comparison':
                selected = log.get('selected_model')
                if selected:
                    selected_counts[selected] = selected_counts.get(selected, 0) + 1
        
        for model in model_counts.keys():
            generated_counts[model] = model_counts[model]
        
        models = list(set(list(selected_counts.keys()) + list(generated_counts.keys())))
        x = np.arange(len(models))
        width = 0.35
        
        generated_vals = [generated_counts.get(m, 0) for m in models]
        selected_vals = [selected_counts.get(m, 0) for m in models]
        
        bars1 = ax3.bar(x - width/2, generated_vals, width, label='Generated', alpha=0.8, color='skyblue', edgecolor='navy')
        bars2 = ax3.bar(x + width/2, selected_vals, width, label='Selected', alpha=0.8, color='lightgreen', edgecolor='darkgreen')
        
        ax3.set_xlabel('Model')
        ax3.set_ylabel('Count')
        ax3.set_title('Generated vs Selected Responses', fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels(models, rotation=45)
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # Plot 4: Selection Rate
        ax4.set_title('Model Selection Rate (%)', fontweight='bold')
        
        if models and generated_vals:
            selection_rates = []
            for i, model in enumerate(models):
                gen = generated_vals[i]
                sel = selected_vals[i] if i < len(selected_vals) else 0
                rate = (sel / gen * 100) if gen > 0 else 0
                selection_rates.append(rate)
            
            colors = ['gold' if rate >= 50 else 'lightcoral' for rate in selection_rates]
            bars = ax4.bar(models, selection_rates, color=colors, edgecolor='black', alpha=0.8)
            ax4.set_ylabel('Selection Rate (%)')
            ax4.set_ylim(0, 100)
            ax4.grid(True, alpha=0.3, axis='y')
            
            for bar, rate in zip(bars, selection_rates):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{rate:.1f}%', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'llm_performance_comprehensive.png'), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(fig_dir, 'llm_performance_comprehensive.pdf'), format='pdf', bbox_inches='tight')
        plt.close()
    
    def _create_rag_analysis_charts(self, fig_dir):
        """Create RAG retrieval analysis charts"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('RAG Retrieval Analysis', fontsize=16, fontweight='bold')
        
        # Collect all scores
        all_scores = []
        module_scores = {}
        
        for rag in self.rag_results:
            scores = rag.get('scores', [])
            all_scores.extend(scores)
            
            module = rag.get('module')
            if module not in module_scores:
                module_scores[module] = []
            module_scores[module].extend(scores)
        
        # Plot 1: Score Distribution Histogram
        if all_scores:
            n, bins, patches = ax1.hist(all_scores, bins=20, alpha=0.7, color='steelblue', 
                                        edgecolor='black', density=True)
            ax1.axvline(x=np.mean(all_scores), color='red', linestyle='--', linewidth=2, 
                       label=f'Mean: {np.mean(all_scores):.3f}')
            ax1.axvline(x=np.median(all_scores), color='green', linestyle='-.', linewidth=2,
                       label=f'Median: {np.median(all_scores):.3f}')
            ax1.axvline(x=0.5, color='orange', linestyle=':', linewidth=2,
                       label='Threshold: 0.5')
            
            # Add normal distribution curve
            from scipy.stats import norm
            mu, sigma = np.mean(all_scores), np.std(all_scores)
            x = np.linspace(min(all_scores), max(all_scores), 100)
            y = norm.pdf(x, mu, sigma)
            ax1.plot(x, y, 'r-', linewidth=2, alpha=0.6, label=f'Normal fit')
            
            ax1.set_xlabel('Retrieval Score')
            ax1.set_ylabel('Density')
            ax1.set_title('RAG Retrieval Score Distribution', fontweight='bold')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # Plot 2: Score by Module (Box Plot)
        if module_scores:
            modules = sorted(module_scores.keys())
            scores_by_module = [module_scores[m] for m in modules]
            
            bp = ax2.boxplot(scores_by_module, labels=[f'Module {m}' for m in modules],
                            patch_artist=True,
                            boxprops=dict(facecolor='lightyellow', color='darkorange'),
                            medianprops=dict(color='red'))
            ax2.set_xlabel('Module')
            ax2.set_ylabel('Retrieval Score')
            ax2.set_title('Retrieval Score Distribution by Module', fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, 1)
            
            # Add mean points and annotations
            for i, scores in enumerate(scores_by_module):
                if scores:
                    mean_val = np.mean(scores)
                    ax2.plot(i+1, mean_val, 'g_', markersize=15)
                    ax2.text(i+1, 0.95, f'n={len(scores)}', ha='center', va='top', fontsize=9)
        
        # Plot 3: Retrieval Count by Query
        retrieval_counts = []
        query_topics = []
        
        for rag in self.rag_results:
            retrieval_counts.append(rag.get('num_results', 0))
            query_topics.append(rag.get('topic', 'Unknown')[:15] + '...')
        
        if retrieval_counts:
            colors = plt.cm.viridis(np.linspace(0, 1, len(retrieval_counts)))
            bars = ax3.bar(range(len(retrieval_counts)), retrieval_counts, color=colors, alpha=0.8, edgecolor='black')
            ax3.set_xlabel('Query Index')
            ax3.set_ylabel('Number of Retrieved Chunks')
            ax3.set_title('Retrieval Count per Query', fontweight='bold')
            ax3.set_xticks(range(len(query_topics)))
            ax3.set_xticklabels(range(1, len(query_topics) + 1))
            ax3.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for bar, count in zip(bars, retrieval_counts):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(count)}', ha='center', va='bottom', fontsize=9)
            
            # Add secondary axis for topic names
            ax3b = ax3.twiny()
            ax3b.set_xlim(ax3.get_xlim())
            ax3b.set_xticks(ax3.get_xticks())
            ax3b.set_xticklabels(query_topics, rotation=45, ha='left', fontsize=8)
            ax3b.set_xlabel('Query Topics', fontsize=10)
        
        # Plot 4: Score vs Retrieval Count Scatter
        if len(self.rag_results) >= 2:
            scores = [np.mean(r.get('scores', [0])) for r in self.rag_results]
            counts = [r.get('num_results', 0) for r in self.rag_results]
            
            scatter = ax4.scatter(counts, scores, alpha=0.7, c=scores, cmap='RdYlGn', 
                                 s=150, edgecolors='black')
            ax4.set_xlabel('Number of Retrieved Chunks')
            ax4.set_ylabel('Average Retrieval Score')
            ax4.set_title('Retrieval Count vs Score Correlation', fontweight='bold')
            ax4.grid(True, alpha=0.3)
            
            # Add correlation line if enough points
            if len(scores) > 1:
                z = np.polyfit(counts, scores, 1)
                p = np.poly1d(z)
                ax4.plot(counts, p(counts), "r--", alpha=0.8, linewidth=2, label=f'Fit: y={z[0]:.3f}x+{z[1]:.3f}')
                
                # Calculate R²
                residuals = scores - p(counts)
                ss_res = np.sum(residuals**2)
                ss_tot = np.sum((scores - np.mean(scores))**2)
                r_squared = 1 - (ss_res / ss_tot)
                ax4.text(0.05, 0.95, f'R² = {r_squared:.3f}', transform=ax4.transAxes, 
                        fontsize=12, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                
                ax4.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'rag_analysis_comprehensive.png'), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(fig_dir, 'rag_analysis_comprehensive.pdf'), format='pdf', bbox_inches='tight')
        plt.close()
    
    def _create_quiz_dashboard(self, fig_dir):
        """Create comprehensive quiz performance dashboard"""
        fig = plt.figure(figsize=(20, 15))
        
        # Create grid layout
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Plot 1: Quiz Scores Bar Chart (span 2 columns)
        ax1 = fig.add_subplot(gs[0, :2])
        topics = [a['topic'][:12] + '...' if len(a['topic']) > 12 else a['topic'] 
                 for a in self.assessments]
        percentages = [a['percentage'] for a in self.assessments]
        grades = [a['grade'] for a in self.assessments]
        
        # Color coding by grade
        grade_colors = {'A': '#4CAF50', 'B': '#8BC34A', 'C': '#FFC107', 
                       'D': '#FF9800', 'F': '#F44336'}
        colors = [grade_colors.get(g, '#9E9E9E') for g in grades]
        
        bars = ax1.bar(range(len(percentages)), percentages, color=colors, 
                      alpha=0.8, edgecolor='black', linewidth=1.5)
        ax1.set_xlabel('Quiz Topic')
        ax1.set_ylabel('Percentage (%)')
        ax1.set_title('Quiz Performance by Topic', fontweight='bold', fontsize=14)
        ax1.set_xticks(range(len(topics)))
        ax1.set_xticklabels([f"Q{i+1}" for i in range(len(topics))])
        ax1.set_ylim(0, 105)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bar, perc, grade, topic in zip(bars, percentages, grades, topics):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{perc:.1f}%\n{grade}', ha='center', va='bottom', fontsize=9)
            # Add topic as x-axis label
            ax1.text(bar.get_x() + bar.get_width()/2., -5, topic, 
                    ha='center', va='top', fontsize=8, rotation=45)
        
        # Create custom legend for grades
        legend_elements = [mpatches.Patch(color=color, label=grade) 
                          for grade, color in grade_colors.items()]
        ax1.legend(handles=legend_elements, title='Grades', loc='upper right', fontsize=9)
        
        # Plot 2: Mastery Level Distribution (Pie Chart)
        ax2 = fig.add_subplot(gs[0, 2])
        mastery_levels = [a['mastery_level'] for a in self.assessments]
        level_counts = {}
        for level in mastery_levels:
            level_counts[level] = level_counts.get(level, 0) + 1
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        wedges, texts, autotexts = ax2.pie(level_counts.values(), labels=level_counts.keys(),
                                          autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100.*sum(level_counts.values()))})',
                                          colors=colors[:len(level_counts)],
                                          startangle=90, textprops={'fontsize': 10})
        ax2.set_title('Mastery Level Distribution', fontweight='bold', fontsize=12)
        
        # Plot 3: Strengths vs Weaknesses Radar Chart
        ax3 = fig.add_subplot(gs[1, 0], projection='polar')
        
        if self.assessments:
            avg_strengths = np.mean([len(a.get('strengths', [])) for a in self.assessments])
            avg_weaknesses = np.mean([len(a.get('weaknesses', [])) for a in self.assessments])
            
            categories = ['Strengths', 'Weaknesses']
            values = [avg_strengths, avg_weaknesses]
            
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            values += values[:1]
            angles += angles[:1]
            
            ax3.plot(angles, values, 'o-', linewidth=3, color='#6A5ACD', markersize=10)
            ax3.fill(angles, values, alpha=0.25, color='#6A5ACD')
            ax3.set_xticks(angles[:-1])
            ax3.set_xticklabels(categories, fontsize=11)
            ax3.set_title('Average Strengths vs Weaknesses', fontweight='bold', fontsize=12)
            ax3.grid(True)
            
            # Add value labels
            for angle, value in zip(angles[:-1], values[:-1]):
                ax3.text(angle, value + 0.1, f'{value:.1f}', ha='center', va='bottom', fontsize=10)
        
        # Plot 4: Question Type Distribution
        ax4 = fig.add_subplot(gs[1, 1])
        
        if self.quiz_results:
            all_q_types = []
            for quiz in self.quiz_results:
                all_q_types.extend(quiz.get('question_types', []))
            
            if all_q_types:
                q_type_counts = {}
                for q_type in all_q_types:
                    q_type_counts[q_type] = q_type_counts.get(q_type, 0) + 1
                
                # Create donut chart
                wedges, texts, autotexts = ax4.pie(q_type_counts.values(), labels=q_type_counts.keys(),
                                                  autopct='%1.1f%%', startangle=90,
                                                  colors=plt.cm.Pastel1(range(len(q_type_counts))),
                                                  wedgeprops=dict(width=0.3, edgecolor='w'))
                ax4.set_title('Question Type Distribution', fontweight='bold', fontsize=12)
        
        # Plot 5: Improvement Over Time
        ax5 = fig.add_subplot(gs[1, 2])
        
        if len(self.assessments) > 1:
            timestamps = [datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) 
                         for a in self.assessments]
            percentages = [a['percentage'] for a in self.assessments]
            topics = [a['topic'][:10] + '...' for a in self.assessments]
            
            # Sort by time
            sorted_data = sorted(zip(timestamps, percentages, topics), key=lambda x: x[0])
            timestamps_sorted, percentages_sorted, topics_sorted = zip(*sorted_data)
            
            ax5.plot(timestamps_sorted, percentages_sorted, 'o-', linewidth=2, markersize=8, 
                    color='#2196F3', markerfacecolor='white', markeredgewidth=2)
            ax5.fill_between(timestamps_sorted, percentages_sorted, alpha=0.3, color='#2196F3')
            ax5.set_xlabel('Assessment Time')
            ax5.set_ylabel('Percentage (%)')
            ax5.set_title('Learning Progress Over Time', fontweight='bold', fontsize=12)
            ax5.grid(True, alpha=0.3)
            ax5.set_ylim(0, 105)
            
            # Add topic labels
            for ts, perc, topic in zip(timestamps_sorted, percentages_sorted, topics_sorted):
                ax5.text(ts, perc + 2, topic, fontsize=8, ha='center', rotation=45)
            
            # Add trend line
            if len(percentages_sorted) > 1:
                x_num = [i for i in range(len(percentages_sorted))]
                z = np.polyfit(x_num, percentages_sorted, 1)
                p = np.poly1d(z)
                ax5.plot(timestamps_sorted, p(x_num), 'r--', alpha=0.8, linewidth=2, 
                        label=f'Trend: {z[0]:.2f}x + {z[1]:.1f}')
                
                # Add trend statistics
                ax5.text(0.05, 0.95, f'Slope: {z[0]:.2f}', transform=ax5.transAxes,
                        fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                ax5.legend(loc='lower right')
        
        # Plot 6: Score Distribution (Histogram)
        ax6 = fig.add_subplot(gs[2, 0])
        
        if percentages:
            n, bins, patches = ax6.hist(percentages, bins=10, alpha=0.7, color='#FF9800',
                                       edgecolor='black', density=True)
            ax6.axvline(x=np.mean(percentages), color='red', linestyle='--', linewidth=2,
                       label=f'Mean: {np.mean(percentages):.1f}%')
            ax6.axvline(x=np.median(percentages), color='green', linestyle='-.', linewidth=2,
                       label=f'Median: {np.median(percentages):.1f}%')
            ax6.set_xlabel('Score (%)')
            ax6.set_ylabel('Density')
            ax6.set_title('Score Distribution', fontweight='bold', fontsize=12)
            ax6.legend(fontsize=9)
            ax6.grid(True, alpha=0.3)
        
        # Plot 7: Performance Metrics Summary
        ax7 = fig.add_subplot(gs[2, 1:])
        
        if self.assessments:
            metrics = {
                'Avg Score': np.mean(percentages),
                'Std Dev': np.std(percentages),
                'Min Score': min(percentages),
                'Max Score': max(percentages),
                'Pass Rate': sum(1 for p in percentages if p >= 60) / len(percentages) * 100,
                'Avg Questions': np.mean([q.get('num_questions', 0) for q in self.quiz_results])
            }
            
            # Create table
            cell_text = [[f'{k}', f'{v:.1f}{"%" if k in ["Avg Score", "Pass Rate"] else ""}'] 
                        for k, v in metrics.items()]
            
            table = ax7.table(cellText=cell_text, loc='center', cellLoc='left',
                             colWidths=[0.4, 0.3])
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            table.scale(1, 2)
            
            # Style table cells
            for (i, j), cell in table.get_celld().items():
                if i == 0:  # Header row
                    cell.set_text_props(weight='bold', color='white')
                    cell.set_facecolor('#4A6572')
                else:
                    if j == 1:  # Value column
                        val = float(cell.get_text().get_text().replace('%', ''))
                        if 'Score' in cell_text[i-1][0]:
                            color = '#C8E6C9' if val >= 70 else '#FFCDD2'
                        else:
                            color = '#F5F5F5'
                        cell.set_facecolor(color)
            
            ax7.set_title('Performance Metrics Summary', fontweight='bold', fontsize=12)
            ax7.axis('off')
        
        plt.suptitle('Quiz Performance Dashboard', fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'quiz_performance_dashboard.png'), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(fig_dir, 'quiz_performance_dashboard.pdf'), format='pdf', bbox_inches='tight')
        plt.close()
    
    def _create_evaluation_heatmap(self, fig_dir):
        """Create heatmap of peer review evaluations"""
        if not self.evaluations:
            return
        
        # Organize data by evaluator and criteria
        evaluators = set()
        criteria = set()
        
        for eval_data in self.evaluations:
            evaluators.add(eval_data['evaluator_model'])
            criteria.update(eval_data['criteria_scores'].keys())
        
        evaluators = sorted(list(evaluators))
        criteria = sorted(list(criteria))
        
        # Create score matrix
        score_matrix = np.zeros((len(evaluators), len(criteria)))
        count_matrix = np.zeros((len(evaluators), len(criteria)))
        
        for eval_data in self.evaluations:
            eval_idx = evaluators.index(eval_data['evaluator_model'])
            for criterion, score in eval_data['criteria_scores'].items():
                crit_idx = criteria.index(criterion)
                score_matrix[eval_idx, crit_idx] += score
                count_matrix[eval_idx, crit_idx] += 1
        
        # Calculate averages
        with np.errstate(divide='ignore', invalid='ignore'):
            avg_matrix = np.true_divide(score_matrix, count_matrix)
            avg_matrix[avg_matrix == np.inf] = 0
            avg_matrix = np.nan_to_num(avg_matrix)
        
        # Create heatmap with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        
        # Subplot 1: Heatmap
        im1 = ax1.imshow(avg_matrix, cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
        
        # Add text annotations
        for i in range(len(evaluators)):
            for j in range(len(criteria)):
                if count_matrix[i, j] > 0:
                    text = ax1.text(j, i, f'{avg_matrix[i, j]:.2f}\n(n={int(count_matrix[i, j])})',
                                 ha="center", va="center", color="black", fontsize=10,
                                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
        
        # Customize plot
        ax1.set_xticks(np.arange(len(criteria)))
        ax1.set_yticks(np.arange(len(evaluators)))
        ax1.set_xticklabels(criteria)
        ax1.set_yticklabels(evaluators)
        ax1.set_title('Peer Review Evaluation Heatmap\n(Average Scores by Evaluator and Criteria)', 
                     fontweight='bold', fontsize=14)
        
        # Rotate x labels
        plt.setp(ax1.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Add colorbar
        cbar1 = ax1.figure.colorbar(im1, ax=ax1)
        cbar1.ax.set_ylabel('Average Score', rotation=-90, va="bottom", fontsize=12)
        
        # Subplot 2: Bar chart of evaluation counts
        eval_counts = {}
        for eval_data in self.evaluations:
            evaluator = eval_data['evaluator_model']
            eval_counts[evaluator] = eval_counts.get(evaluator, 0) + 1
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(eval_counts)))
        bars = ax2.bar(eval_counts.keys(), eval_counts.values(), color=colors, alpha=0.8, edgecolor='black')
        ax2.set_xlabel('Evaluator')
        ax2.set_ylabel('Number of Evaluations')
        ax2.set_title('Evaluation Count by Evaluator', fontweight='bold', fontsize=14)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontsize=10)
        
        # Add overall statistics
        overall_stats = {
            'Total Evaluations': len(self.evaluations),
            'Avg Score': np.mean([e['weighted_score'] for e in self.evaluations]),
            'Std Dev': np.std([e['weighted_score'] for e in self.evaluations])
        }
        
        stats_text = '\n'.join([f'{k}: {v:.3f}' if isinstance(v, float) else f'{k}: {v}' 
                               for k, v in overall_stats.items()])
        ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'peer_review_heatmap.png'), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(fig_dir, 'peer_review_heatmap.pdf'), format='pdf', bbox_inches='tight')
        plt.close()
    
    def _create_performance_timeline(self, fig_dir):
        """Create system performance timeline"""
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Extract timeline data
        event_data = []
        for log in self.session_log:
            if log['type'] in ['query', 'final_response', 'quiz_generation', 'quiz_evaluation']:
                ts = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                event_data.append({
                    'time': ts,
                    'type': log['type'],
                    'data': log
                })
        
        # Create timeline plot
        if len(event_data) > 1:
            # Sort by time
            event_data.sort(key=lambda x: x['time'])
            
            # Create event markers
            event_colors = {
                'query': '#2196F3',  # Blue
                'final_response': '#4CAF50',  # Green
                'quiz_generation': '#FF9800',  # Orange
                'quiz_evaluation': '#F44336'  # Red
            }
            
            event_shapes = {
                'query': 'o',
                'final_response': 's',
                'quiz_generation': '^',
                'quiz_evaluation': 'D'
            }
            
            event_labels = {
                'query': 'Query',
                'final_response': 'Response',
                'quiz_generation': 'Quiz Generated',
                'quiz_evaluation': 'Quiz Evaluated'
            }
            
            # Plot events
            y_positions = {}
            for i, event in enumerate(event_data):
                event_type = event['type']
                if event_type not in y_positions:
                    y_positions[event_type] = list(event_colors.keys()).index(event_type) * 2
                
                y = y_positions[event_type]
                color = event_colors[event_type]
                shape = event_shapes[event_type]
                
                ax.plot(event['time'], y, shape, color=color, markersize=12, 
                       markerfacecolor='white', markeredgewidth=2)
                
                # Add event label
                label_text = ''
                if event_type == 'query':
                    query = event['data'].get('query', '')[:20] + '...'
                    label_text = f"Q: {query}"
                elif event_type == 'final_response':
                    topic = event['data'].get('topic', '')[:15] + '...'
                    label_text = f"R: {topic}"
                elif event_type == 'quiz_evaluation':
                    score = event['data'].get('percentage', 0)
                    label_text = f"Score: {score:.1f}%"
                
                if label_text:
                    ax.text(event['time'], y + 0.3, label_text, fontsize=8, 
                           rotation=45, ha='left', va='bottom')
            
            # Add connecting lines for sequences
            for i in range(len(event_data) - 1):
                if event_data[i+1]['time'] - event_data[i]['time'] < pd.Timedelta(minutes=5):
                    ax.plot([event_data[i]['time'], event_data[i+1]['time']],
                           [y_positions[event_data[i]['type']], y_positions[event_data[i+1]['type']]],
                           'k-', alpha=0.3, linewidth=1)
            
            ax.set_yticks(list(y_positions.values()))
            ax.set_yticklabels([event_labels.get(et, et) for et in y_positions.keys()])
            ax.set_xlabel('Time', fontsize=12)
            ax.set_title('System Activity Timeline', fontweight='bold', fontsize=14)
            ax.grid(True, alpha=0.3, axis='x')
            
            # Format x-axis for time
            plt.xticks(rotation=45)
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S'))
        
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'system_timeline.png'), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(fig_dir, 'system_timeline.pdf'), format='pdf', bbox_inches='tight')
        plt.close()
    
    def _create_learning_style_chart(self, fig_dir):
        """Create learning style distribution chart"""
        # Extract learning styles from queries
        styles = []
        for log in self.session_log:
            if log['type'] == 'query':
                style = log['routing_info'].get('style')
                if style:
                    styles.append(style)
        
        if styles:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            style_counts = {}
            for style in styles:
                style_counts[style] = style_counts.get(style, 0) + 1
            
            # Plot 1: Bar chart
            style_names = list(style_counts.keys())
            counts = list(style_counts.values())
            
            colors = plt.cm.Set2(np.linspace(0, 1, len(style_names)))
            bars = ax1.bar(style_names, counts, color=colors, alpha=0.8, edgecolor='black')
            
            ax1.set_xlabel('Learning Style', fontsize=12)
            ax1.set_ylabel('Number of Queries', fontsize=12)
            ax1.set_title('Learning Style Distribution (Bar Chart)', fontweight='bold', fontsize=14)
            ax1.grid(True, alpha=0.3, axis='y')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(height)}', ha='center', va='bottom', fontsize=10)
            
            # Plot 2: Donut chart
            wedges, texts, autotexts = ax2.pie(counts, labels=style_names, colors=colors,
                                              autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100.*sum(counts))})',
                                              startangle=90, wedgeprops=dict(width=0.3, edgecolor='w'))
            ax2.set_title('Learning Style Distribution (Donut Chart)', fontweight='bold', fontsize=14)
            
            # Add overall statistics
            total_queries = sum(counts)
            ax2.text(0, -1.3, f'Total Queries: {total_queries}', ha='center', fontsize=11,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            plt.tight_layout()
            plt.savefig(os.path.join(fig_dir, 'learning_style_distribution.png'), dpi=300, bbox_inches='tight')
            plt.savefig(os.path.join(fig_dir, 'learning_style_distribution.pdf'), format='pdf', bbox_inches='tight')
            plt.close()
    
    def _create_model_selection_analysis(self, fig_dir):
        """Create model selection vs evaluation analysis"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # This requires more detailed tracking
        ax.text(0.5, 0.5, 'Model Selection Analysis\n\nRequires Detailed Tracking of:\n'
               '- Selection reasons\n- Evaluation scores correlation\n- Response quality metrics\n\n'
               'Enable detailed logging in response_ranker.py\nfor comprehensive analysis.',
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=14, 
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
        ax.set_title('Model Selection vs Evaluation Analysis', fontweight='bold', fontsize=16)
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'model_selection_analysis.png'), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(fig_dir, 'model_selection_analysis.pdf'), format='pdf', bbox_inches='tight')
        plt.close()
    
    def _create_system_overview_dashboard(self, fig_dir):
        """Create comprehensive system overview dashboard"""
        fig = plt.figure(figsize=(20, 12))
        
        # Create grid layout
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # Plot 1: System Usage Summary
        ax1 = fig.add_subplot(gs[0, 0])
        stats = self.generate_summary_statistics()
        
        usage_data = {
            'Queries': stats.get('total_queries', 0),
            'LLM Responses': stats.get('total_llm_responses', 0),
            'Quizzes': stats.get('total_quizzes', 0),
            'Assessments': stats.get('total_assessments', 0)
        }
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        bars = ax1.bar(usage_data.keys(), usage_data.values(), color=colors, alpha=0.8, edgecolor='black')
        ax1.set_title('System Usage Summary', fontweight='bold', fontsize=14)
        ax1.set_ylabel('Count')
        ax1.grid(True, alpha=0.3, axis='y')
        
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom', fontsize=10)
        
        # Plot 2: Performance Metrics
        ax2 = fig.add_subplot(gs[0, 1])
        
        perf_metrics = {}
        if 'rag_avg_score' in stats:
            perf_metrics['RAG Score'] = stats['rag_avg_score']
        if 'quiz_avg_percentage' in stats:
            perf_metrics['Quiz Score'] = stats['quiz_avg_percentage'] / 100  # Normalize to 0-1
        if 'eval_avg_score' in stats:
            perf_metrics['Eval Score'] = stats['eval_avg_score']
        
        if perf_metrics:
            colors = plt.cm.RdYlGn(np.linspace(0.3, 0.7, len(perf_metrics)))
            bars = ax2.bar(perf_metrics.keys(), perf_metrics.values(), color=colors, alpha=0.8, edgecolor='black')
            ax2.set_title('Performance Metrics (0-1 scale)', fontweight='bold', fontsize=14)
            ax2.set_ylim(0, 1)
            ax2.grid(True, alpha=0.3, axis='y')
            
            for bar, (metric, value) in zip(bars, perf_metrics.items()):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                        f'{value:.3f}', ha='center', va='bottom', fontsize=10)
        
        # Plot 3: LLM Model Distribution
        ax3 = fig.add_subplot(gs[0, 2])
        
        if 'llm_response_counts' in stats:
            model_counts = stats['llm_response_counts']
            colors = plt.cm.Pastel1(range(len(model_counts)))
            wedges, texts, autotexts = ax3.pie(model_counts.values(), labels=model_counts.keys(),
                                              autopct='%1.1f%%', colors=colors, startangle=90)
            ax3.set_title('LLM Model Distribution', fontweight='bold', fontsize=14)
        
        # Plot 4: Learning Style Impact (if available)
        ax4 = fig.add_subplot(gs[1, 0])
        
        if 'learning_styles' in stats:
            style_data = stats['learning_styles']
            colors = plt.cm.Set3(np.linspace(0, 1, len(style_data)))
            bars = ax4.bar(style_data.keys(), style_data.values(), color=colors, alpha=0.8, edgecolor='black')
            ax4.set_title('Learning Style Preferences', fontweight='bold', fontsize=14)
            ax4.set_xlabel('Learning Style')
            ax4.set_ylabel('Count')
            ax4.grid(True, alpha=0.3, axis='y')
            
            for bar in bars:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom', fontsize=10)
        
        # Plot 5: Session Duration
        ax5 = fig.add_subplot(gs[1, 1])
        
        if stats.get('start_time') and stats.get('end_time'):
            start = datetime.fromisoformat(stats['start_time'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(stats['end_time'].replace('Z', '+00:00'))
            duration = (end - start).total_seconds() / 60  # Convert to minutes
            
            ax5.text(0.5, 0.5, f'Session Duration:\n{duration:.1f} minutes\n\n'
                    f'Start: {start.strftime("%H:%M:%S")}\n'
                    f'End: {end.strftime("%H:%M:%S")}',
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax5.transAxes, fontsize=12,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
            ax5.set_title('Session Information', fontweight='bold', fontsize=14)
            ax5.axis('off')
        
        # Plot 6: Recommendations
        ax6 = fig.add_subplot(gs[1, 2])
        
        recommendations = [
            "✓ Collect more diverse queries",
            "✓ Test all learning styles",
            "✓ Include quiz assessments",
            "✓ Monitor LLM performance",
            "✓ Check RAG retrieval quality",
            "✓ Validate evaluation scores"
        ]
        
        ax6.text(0.05, 0.95, 'Recommendations for Next Run:', 
                transform=ax6.transAxes, fontsize=12, fontweight='bold',
                verticalalignment='top')
        
        for i, rec in enumerate(recommendations):
            ax6.text(0.05, 0.85 - i*0.1, rec, transform=ax6.transAxes, fontsize=10,
                    verticalalignment='top')
        
        ax6.set_title('Analysis Recommendations', fontweight='bold', fontsize=14)
        ax6.axis('off')
        
        plt.suptitle('Personalized Learning System - Comprehensive Dashboard', 
                    fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, 'system_overview_dashboard.png'), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(fig_dir, 'system_overview_dashboard.pdf'), format='pdf', bbox_inches='tight')
        plt.close()
    
    def save_session(self):
        """Save complete session data"""
        print(f"\n{'='*60}")
        print("SAVING SESSION RESULTS")
        print('='*60)
        
        # Generate summary
        stats = self.generate_summary_statistics()
        
        # Create visualizations
        self.create_visualizations()
        
        # Write summary to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write("SESSION SUMMARY STATISTICS\n")
            f.write(f"{'='*80}\n\n")
            
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    f.write(f"{key}: {value}\n")
                elif isinstance(value, list):
                    f.write(f"{key}: {', '.join(map(str, value))}\n")
                elif isinstance(value, dict):
                    f.write(f"{key}:\n")
                    for k, v in value.items():
                        f.write(f"  - {k}: {v}\n")
                else:
                    f.write(f"{key}: {value}\n")
        
        # Save as JSON for programmatic access
        json_file = os.path.join(self.log_dir, f"session_{self.session_id}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'session_log': self.session_log,
                'llm_responses': self.llm_responses,
                'rag_results': self.rag_results,
                'quiz_results': self.quiz_results,
                'assessments': self.assessments,
                'evaluations': self.evaluations,
                'web_content': self.web_content,
                'statistics': stats
            }, f, indent=2, ensure_ascii=False)
        
        # Generate research report
        self.generate_research_report()
        
        print(f"\n📊 Session results saved to:")
        print(f"   📄 Text Log: {self.log_file}")
        print(f"   📊 JSON Data: {json_file}")
        print(f"   📈 Figures: {os.path.join(self.log_dir, 'figures')}")
        print(f"   📋 Research Report: {os.path.join(self.log_dir, f'research_report_{self.session_id}.md')}")
        
        return self.log_file
    
    def generate_research_report(self):
        """Generate a comprehensive research report with graphs"""
        report_file = os.path.join(self.log_dir, f"research_report_{self.session_id}.md")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Personalized Learning System Research Report\n\n")
            f.write(f"**Session ID**: {self.session_id}\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary Statistics
            stats = self.generate_summary_statistics()
            f.write("## Summary Statistics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    f.write(f"| {key} | {value} |\n")
            
            # Key Performance Indicators
            f.write("\n## Key Performance Indicators\n\n")
            f.write("| KPI | Value | Status |\n")
            f.write("|-----|-------|--------|\n")
            
            kpis = [
                ("Total Queries", stats.get('total_queries', 0), "≥5 queries for analysis"),
                ("RAG Average Score", stats.get('rag_avg_score', 0), "≥0.6 for good retrieval"),
                ("Quiz Average Score", stats.get('quiz_avg_percentage', 0), "≥60% for good learning"),
                ("Evaluation Average Score", stats.get('eval_avg_score', 0), "≥0.7 for good evaluations"),
                ("LLM Models Used", len(stats.get('llm_models_used', [])), "All 3 models should be used")
            ]
            
            for name, value, criteria in kpis:
                if isinstance(value, float):
                    status = "✅ Good" if (name == "RAG Average Score" and value >= 0.6) or \
                                         (name == "Quiz Average Score" and value >= 60) or \
                                         (name == "Evaluation Average Score" and value >= 0.7) or \
                                         (name == "LLM Models Used" and value >= 3) else "⚠️ Needs Improvement"
                    display_value = f"{value:.3f}" if isinstance(value, float) else value
                    f.write(f"| {name} | {display_value} | {status} |\n")
            
            # Graph References
            f.write("\n## Visualizations\n\n")
            figures_dir = os.path.join(self.log_dir, "figures")
            if os.path.exists(figures_dir):
                figures = sorted(os.listdir(figures_dir))
                for fig in figures:
                    if fig.endswith('.png'):
                        fig_name = fig.replace('.png', '').replace('_', ' ').title()
                        f.write(f"### {fig_name}\n\n")
                        f.write(f"![{fig_name}](figures/{fig})\n\n")
                        f.write(f"*Description: {self._get_figure_description(fig)}*\n\n")
            
            # Key Findings
            f.write("\n## Key Findings\n\n")
            f.write("### 1. LLM Performance\n")
            f.write("- [Add observations about model performance, selection rates, response lengths]\n\n")
            
            f.write("### 2. RAG Effectiveness\n")
            f.write("- [Add observations about retrieval scores, module performance, correlation with query complexity]\n\n")
            
            f.write("### 3. Learning Assessment\n")
            f.write("- [Add observations about quiz scores, mastery levels, learning progress]\n\n")
            
            f.write("### 4. System Performance\n")
            f.write("- [Add observations about response times, system reliability, user engagement]\n\n")
            
            # Recommendations
            f.write("## Recommendations for Improvement\n\n")
            f.write("1. **Data Quality**: [Recommendations based on RAG scores]\n")
            f.write("2. **Model Selection**: [Recommendations based on LLM performance]\n")
            f.write("3. **Assessment Design**: [Recommendations based on quiz results]\n")
            f.write("4. **User Experience**: [Recommendations based on learning styles]\n")
            f.write("5. **System Optimization**: [Technical recommendations]\n\n")
            
            # Appendix
            f.write("## Appendix: Raw Data\n\n")
            f.write(f"- Complete session log: `session_{self.session_id}.txt`\n")
            f.write(f"- Structured JSON data: `session_{self.session_id}.json`\n")
            f.write(f"- All visualizations: `figures/` directory\n")
        
        print(f"📋 Research report saved: {report_file}")
        return report_file
    
    def _get_figure_description(self, filename: str) -> str:
        """Get description for each figure"""
        descriptions = {
            'llm_performance_comprehensive.png': 'Comprehensive analysis of LLM performance including response lengths, model usage, and selection rates',
            'rag_analysis_comprehensive.png': 'Detailed RAG retrieval analysis showing score distributions, module performance, and retrieval patterns',
            'quiz_performance_dashboard.png': 'Complete quiz performance dashboard with scores, mastery levels, and learning progress',
            'peer_review_heatmap.png': 'Heatmap showing peer review evaluation scores across different criteria and evaluators',
            'system_timeline.png': 'Timeline visualization of system activities and user interactions',
            'learning_style_distribution.png': 'Distribution of learning style preferences among user queries',
            'system_overview_dashboard.png': 'Comprehensive system overview showing usage statistics and performance metrics',
            'model_selection_analysis.png': 'Analysis of model selection patterns and evaluation correlations'
        }
        return descriptions.get(filename, 'Visualization of system performance data')

# Create a global instance
result_logger = ResultLogger()