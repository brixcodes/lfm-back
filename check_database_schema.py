#!/usr/bin/env python3
"""
Script to check database schema and identify missing fields
"""
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import get_session_async
from sqlalchemy import text

async def check_training_sessions_schema():
    """Check the training_sessions table schema"""
    try:
        async for session in get_session_async():
            # Check if the table exists
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'training_sessions'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                print("❌ training_sessions table does not exist!")
                return
            
            print("✅ training_sessions table exists")
            
            # Check for specific columns
            columns_to_check = [
                'center_id',
                'registration_deadline', 
                'available_slots',
                'moodle_course_id'
            ]
            
            missing_columns = []
            for column in columns_to_check:
                result = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'training_sessions'
                        AND column_name = '{column}'
                    );
                """))
                column_exists = result.scalar()
                
                if column_exists:
                    print(f"✅ Column '{column}' exists")
                else:
                    print(f"❌ Column '{column}' is missing")
                    missing_columns.append(column)
            
            if missing_columns:
                print(f"\n⚠️  Missing columns: {', '.join(missing_columns)}")
                print("💡 Run 'python run_migrations.py' to add missing columns")
            else:
                print("\n✅ All required columns are present")
            
            break
            
    except Exception as e:
        print(f"Error checking schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_training_sessions_schema())
