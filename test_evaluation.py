#!/usr/bin/env python3
"""
Test script for RAG evaluation system
"""
import asyncio
import os
import sys
sys.path.append('/Users/neilkanungo/Documents/code-repos/simple-rag-app/backend')

from services.evaluation_service import EvaluationService

async def test_evaluation():
    """Test the evaluation service"""
    eval_service = EvaluationService()
    
    # Test data
    query = "What are the main benefits of machine learning?"
    response = "Machine learning offers several key benefits including automated decision making, pattern recognition, and improved efficiency in data processing."
    contexts = [
        "Machine learning enables automated decision making by learning from data patterns.",
        "One of the main advantages of ML is its ability to recognize complex patterns in large datasets.",
        "ML systems can process data more efficiently than traditional programming approaches."
    ]
    sources = ["document1.pdf", "document2.pdf"]
    
    print("Testing RAG evaluation system...")
    print(f"Query: {query}")
    print(f"Response: {response}")
    print(f"Number of contexts: {len(contexts)}")
    print(f"Sources: {sources}")
    print("\n" + "="*50 + "\n")
    
    # Run evaluation
    results = await eval_service.evaluate_response(query, response, contexts, sources)
    
    print("EVALUATION RESULTS:")
    print(f"Overall Score: {results.get('overall_score', 0):.2f}")
    print("\nDetailed Metrics:")
    
    for metric_name, metric_data in results.get('metrics', {}).items():
        if isinstance(metric_data, dict) and 'score' in metric_data:
            score = metric_data['score']
            description = metric_data.get('description', 'No description')
            print(f"  {metric_name.capitalize()}: {score:.2f} - {description}")
        else:
            print(f"  {metric_name.capitalize()}: {metric_data}")
    
    # Test summary
    print("\n" + "="*50 + "\n")
    summary = eval_service.get_evaluation_summary()
    print("EVALUATION SUMMARY:")
    print(f"Total evaluations: {summary.get('total_evaluations', 0)}")
    print(f"Recent trend: {summary.get('recent_trend', 'N/A')}")
    
    if summary.get('average_scores'):
        print("\nAverage Scores:")
        for metric, score in summary['average_scores'].items():
            print(f"  {metric.capitalize()}: {score:.2f}")

if __name__ == "__main__":
    # Make sure we have OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key in the .env file")
        sys.exit(1)
    
    asyncio.run(test_evaluation())
