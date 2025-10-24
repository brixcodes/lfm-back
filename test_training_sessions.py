#!/usr/bin/env python3
"""
Test script to debug the training-sessions endpoint issue
"""
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import get_session_async
from src.api.training.services.training import TrainingService
from src.api.training.schemas import TrainingSessionFilter

async def test_training_sessions():
    """Test the training sessions endpoint"""
    try:
        print("Testing training sessions endpoint...")
        
        # Create a filter similar to the request
        filters = TrainingSessionFilter(
            page=1,
            page_size=1000,
            order_by="created_at",
            asc="desc"
        )
        
        print(f"Filter: {filters}")
        
        # Test database connection
        async for session in get_session_async():
            print("Database connection successful")
            
            # Test the service
            training_service = TrainingService(session)
            sessions, total = await training_service.list_training_sessions(filters)
            
            print(f"Found {len(sessions)} training sessions")
            print(f"Total: {total}")
            
            if sessions:
                print("First session:", sessions[0])
            else:
                print("No training sessions found")
            
            break
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_training_sessions())
