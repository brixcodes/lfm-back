    async def get_payment_statistics(self) -> dict:
        """Get payment statistics for job applications"""
        # Total applications
        total_stmt = select(func.count(JobApplication.id)).where(JobApplication.delete_at.is_(None))
        total_result = await self.session.execute(total_stmt)
        total_applications = total_result.scalar() or 0
        
        # Paid applications
        paid_stmt = select(func.count(JobApplication.id)).where(
            JobApplication.delete_at.is_(None),
            JobApplication.payment_id.is_not(None)
        )
        paid_result = await self.session.execute(paid_stmt)
        paid_applications = paid_result.scalar() or 0
        
        # Unpaid applications
        unpaid_applications = total_applications - paid_applications
        
        # Total revenue from paid applications
        revenue_stmt = select(func.sum(JobApplication.submission_fee)).where(
            JobApplication.delete_at.is_(None),
            JobApplication.payment_id.is_not(None)
        )
        revenue_result = await self.session.execute(revenue_stmt)
        total_revenue = revenue_result.scalar() or 0.0
        
        return {
            "total_applications": total_applications,
            "paid_applications": paid_applications,
            "unpaid_applications": unpaid_applications,
            "payment_rate": round((paid_applications / total_applications * 100) if total_applications > 0 else 0, 2),
            "total_revenue": float(total_revenue),
            "currency": "EUR"  # Default currency
        }
