import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
import os
from openai import OpenAI
import statistics

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Store evaluation history
        self.evaluation_history = []
    
    async def evaluate_response(
        self, 
        query: str, 
        response: str, 
        retrieved_contexts: List[str],
        sources: List[str]
    ) -> Dict:
        """Evaluate a RAG response using multiple metrics"""
        try:
            evaluation_results = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "response": response,
                "sources": sources,
                "metrics": {}
            }
            
            # Run evaluations in parallel
            tasks = [
                self._evaluate_relevance(query, response),
                self._evaluate_faithfulness(response, retrieved_contexts),
                self._evaluate_completeness(query, response),
                self._evaluate_clarity(response),
                self._calculate_retrieval_metrics(query, retrieved_contexts)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            metric_names = ["relevance", "faithfulness", "completeness", "clarity", "retrieval"]
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in {metric_names[i]} evaluation: {str(result)}")
                    evaluation_results["metrics"][metric_names[i]] = {"score": 0.0, "error": str(result)}
                else:
                    evaluation_results["metrics"][metric_names[i]] = result
            
            # Calculate overall score
            scores = [
                evaluation_results["metrics"][metric].get("score", 0.0) 
                for metric in evaluation_results["metrics"]
                if "error" not in evaluation_results["metrics"][metric]
            ]
            
            evaluation_results["overall_score"] = statistics.mean(scores) if scores else 0.0
            
            # Store in history
            self.evaluation_history.append(evaluation_results)
            
            # Keep only last 100 evaluations
            if len(self.evaluation_history) > 100:
                self.evaluation_history = self.evaluation_history[-100:]
            
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Error in evaluation: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "response": response,
                "sources": sources,
                "metrics": {},
                "overall_score": 0.0,
                "error": str(e)
            }
    
    async def _evaluate_relevance(self, query: str, response: str) -> Dict:
        """Evaluate how relevant the response is to the query"""
        try:
            prompt = f"""
            Rate the relevance of the response to the query on a scale of 0.0 to 1.0.
            
            Query: {query}
            Response: {response}
            
            Criteria:
            - 1.0: Response directly and completely addresses the query
            - 0.8: Response mostly addresses the query with minor gaps
            - 0.6: Response partially addresses the query
            - 0.4: Response somewhat relates but misses key aspects
            - 0.2: Response barely relates to the query
            - 0.0: Response is completely irrelevant
            
            Provide only a numeric score between 0.0 and 1.0.
            """
            
            result = await self._get_llm_score(prompt)
            return {
                "score": result,
                "description": "Measures how well the response addresses the user's query"
            }
        except Exception as e:
            logger.error(f"Relevance evaluation error: {str(e)}")
            return {"score": 0.0, "error": str(e)}
    
    async def _evaluate_faithfulness(self, response: str, contexts: List[str]) -> Dict:
        """Evaluate if the response is faithful to the retrieved contexts"""
        try:
            context_text = "\n\n".join(contexts[:3])  # Use top 3 contexts
            
            prompt = f"""
            Rate the faithfulness of the response to the provided context on a scale of 0.0 to 1.0.
            
            Context: {context_text}
            Response: {response}
            
            Criteria:
            - 1.0: Response is completely supported by the context, no hallucinations
            - 0.8: Response is mostly supported with minor unsupported details
            - 0.6: Response is partially supported but has some unsupported claims
            - 0.4: Response has significant unsupported or contradictory information
            - 0.2: Response is mostly unsupported by the context
            - 0.0: Response contradicts or is completely unsupported by context
            
            Provide only a numeric score between 0.0 and 1.0.
            """
            
            result = await self._get_llm_score(prompt)
            return {
                "score": result,
                "description": "Measures if the response is grounded in the retrieved context"
            }
        except Exception as e:
            logger.error(f"Faithfulness evaluation error: {str(e)}")
            return {"score": 0.0, "error": str(e)}
    
    async def _evaluate_completeness(self, query: str, response: str) -> Dict:
        """Evaluate completeness of the response"""
        try:
            prompt = f"""
            Rate the completeness of the response to the query on a scale of 0.0 to 1.0.
            
            Query: {query}
            Response: {response}
            
            Criteria:
            - 1.0: Response thoroughly answers all aspects of the query
            - 0.8: Response covers most aspects with minor gaps
            - 0.6: Response covers main points but misses some important aspects
            - 0.4: Response covers some aspects but leaves significant gaps
            - 0.2: Response only partially addresses the query
            - 0.0: Response fails to address the query adequately
            
            Provide only a numeric score between 0.0 and 1.0.
            """
            
            result = await self._get_llm_score(prompt)
            return {
                "score": result,
                "description": "Measures how thoroughly the response addresses the query"
            }
        except Exception as e:
            logger.error(f"Completeness evaluation error: {str(e)}")
            return {"score": 0.0, "error": str(e)}
    
    async def _evaluate_clarity(self, response: str) -> Dict:
        """Evaluate clarity and readability of the response"""
        try:
            prompt = f"""
            Rate the clarity and readability of the response on a scale of 0.0 to 1.0.
            
            Response: {response}
            
            Criteria:
            - 1.0: Response is very clear, well-structured, and easy to understand
            - 0.8: Response is mostly clear with good structure
            - 0.6: Response is reasonably clear but could be better structured
            - 0.4: Response is somewhat unclear or poorly structured
            - 0.2: Response is difficult to understand
            - 0.0: Response is very unclear or confusing
            
            Provide only a numeric score between 0.0 and 1.0.
            """
            
            result = await self._get_llm_score(prompt)
            return {
                "score": result,
                "description": "Measures how clear and well-structured the response is"
            }
        except Exception as e:
            logger.error(f"Clarity evaluation error: {str(e)}")
            return {"score": 0.0, "error": str(e)}
    
    async def _calculate_retrieval_metrics(self, query: str, contexts: List[str]) -> Dict:
        """Calculate retrieval quality metrics"""
        try:
            if not contexts:
                return {
                    "score": 0.0,
                    "description": "No contexts retrieved",
                    "num_contexts": 0
                }
            
            # Simple retrieval score based on number and diversity of contexts
            num_contexts = len(contexts)
            diversity_score = len(set(contexts)) / len(contexts) if contexts else 0
            
            # Score based on having good number of diverse contexts
            retrieval_score = min(1.0, (num_contexts / 5.0) * diversity_score)
            
            return {
                "score": retrieval_score,
                "description": f"Retrieved {num_contexts} contexts with {diversity_score:.2f} diversity",
                "num_contexts": num_contexts,
                "diversity": diversity_score
            }
        except Exception as e:
            logger.error(f"Retrieval metrics error: {str(e)}")
            return {"score": 0.0, "error": str(e)}
    
    async def _get_llm_score(self, prompt: str) -> float:
        """Get a numeric score from LLM evaluation"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract numeric score
            try:
                score = float(content)
                return max(0.0, min(1.0, score))  # Clamp between 0 and 1
            except ValueError:
                # Try to extract number from text
                import re
                numbers = re.findall(r'\d+\.?\d*', content)
                if numbers:
                    score = float(numbers[0])
                    if score > 1.0 and score <= 10.0:  # Handle 0-10 scale
                        score = score / 10.0
                    return max(0.0, min(1.0, score))
                else:
                    logger.warning(f"Could not parse score from: {content}")
                    return 0.5
                    
        except Exception as e:
            logger.error(f"Error getting LLM score: {str(e)}")
            return 0.5
    
    def get_evaluation_summary(self) -> Dict:
        """Get summary of evaluation metrics"""
        if not self.evaluation_history:
            return {
                "total_evaluations": 0,
                "average_scores": {},
                "recent_trend": "No data"
            }
        
        # Calculate averages
        recent_evaluations = self.evaluation_history[-10:]  # Last 10
        all_evaluations = self.evaluation_history
        
        def calculate_averages(evaluations):
            if not evaluations:
                return {}
            
            metrics = ["relevance", "faithfulness", "completeness", "clarity", "retrieval"]
            averages = {}
            
            for metric in metrics:
                scores = [
                    eval_data["metrics"].get(metric, {}).get("score", 0.0)
                    for eval_data in evaluations
                    if metric in eval_data.get("metrics", {})
                ]
                averages[metric] = statistics.mean(scores) if scores else 0.0
            
            overall_scores = [eval_data.get("overall_score", 0.0) for eval_data in evaluations]
            averages["overall"] = statistics.mean(overall_scores) if overall_scores else 0.0
            
            return averages
        
        recent_avg = calculate_averages(recent_evaluations)
        all_avg = calculate_averages(all_evaluations)
        
        # Determine trend
        if len(self.evaluation_history) < 2:
            trend = "Insufficient data"
        else:
            recent_score = recent_avg.get("overall", 0.0)
            all_score = all_avg.get("overall", 0.0)
            
            if recent_score > all_score + 0.05:
                trend = "Improving"
            elif recent_score < all_score - 0.05:
                trend = "Declining"
            else:
                trend = "Stable"
        
        return {
            "total_evaluations": len(self.evaluation_history),
            "average_scores": all_avg,
            "recent_scores": recent_avg,
            "recent_trend": trend,
            "last_evaluation": self.evaluation_history[-1]["timestamp"] if self.evaluation_history else None
        }
