#!/usr/bin/env python3
"""
Script to run database migrations
"""
import asyncio
import sys
import os
from alembic.config import Config
from alembic import command

def run_migrations():
    """Run database migrations"""
    try:
        # Get the alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Run the upgrade command
        print("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        print("Database migrations completed successfully!")
        
    except Exception as e:
        print(f"Error running migrations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
