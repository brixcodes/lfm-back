from fastapi import APIRouter, Depends
from sqlmodel import select, func, and_, or_
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session_async

router = APIRouter()

@router.get("/health")
async def health_check():
    """Endpoint de santé pour vérifier que l'API fonctionne"""
    return {
        "status": "healthy",
        "message": "Dashboard API is working",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/basic-stats")
async def get_basic_statistics():
    """Endpoint simplifié pour les statistiques de base"""
    return {
        "users": {
            "total": 0,
            "new_this_month": 0
        },
        "trainings": {
            "total_active": 0,
            "total_inactive": 0
        },
        "applications": {
            "total_training_applications": 0,
            "total_job_applications": 0
        },
        "blog": {
            "total_posts": 0,
            "published_posts": 0
        },
        "job_offers": {
            "total": 0,
            "available": 0
        },
        "reclamations": {
            "total": 0
        },
        "payments": {
            "total_payments": 0
        }
    }

@router.get("/comprehensive-stats")
async def get_comprehensive_statistics(
    db: AsyncSession = Depends(get_session_async)
):
    """Récupérer toutes les statistiques du système"""
    
    try:
        # ===== STATISTIQUES UTILISATEURS =====
        # Import dynamique pour éviter les problèmes de dépendances
        from src.api.user.models import User, Role, UserRole
        
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0
        
        # Utilisateurs par statut
        users_by_status = {}
        for status in ["active", "inactive", "blocked", "deleted"]:
            result = await db.execute(
                select(func.count(User.id)).where(User.status == status)
            )
            users_by_status[status] = result.scalar() or 0
        
        # Utilisateurs par type
        user_types_result = await db.execute(
            select(User.user_type, func.count(User.id))
            .group_by(User.user_type)
        )
        user_types = {user_type: count for user_type, count in user_types_result.all()}
        
        # Utilisateurs par pays
        users_by_country_result = await db.execute(
            select(User.country_code, func.count(User.id))
            .where(User.country_code.isnot(None))
            .group_by(User.country_code)
        )
        users_by_country = {country: count for country, count in users_by_country_result.all()}
        
        # Utilisateurs avec 2FA activé
        two_factor_enabled_result = await db.execute(
            select(func.count(User.id)).where(User.two_factor_enabled == True)
        )
        two_factor_enabled = two_factor_enabled_result.scalar() or 0
        
        # Utilisateurs créés ce mois
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users_this_month_result = await db.execute(
            select(func.count(User.id)).where(User.created_at >= this_month_start)
        )
        new_users_this_month = new_users_this_month_result.scalar() or 0
        
        # ===== STATISTIQUES FORMATIONS =====
        try:
            from src.api.training.models import Training, TrainingSession, TrainingSessionParticipant, StudentApplication, Specialty
            
            # Formations actives/inactives
            active_trainings_result = await db.execute(
                select(func.count(Training.id)).where(Training.status == "ACTIVE")
            )
            active_trainings = active_trainings_result.scalar() or 0
            
            inactive_trainings_result = await db.execute(
                select(func.count(Training.id)).where(Training.status == "INACTIVE")
            )
            inactive_trainings = inactive_trainings_result.scalar() or 0
            
            # Sessions de formation par statut
            sessions_by_status = {}
            for status in ["OPEN_FOR_REGISTRATION", "CLOSE_FOR_REGISTRATION", "ONGOING", "COMPLETED"]:
                result = await db.execute(
                    select(func.count(TrainingSession.id)).where(TrainingSession.status == status)
                )
                sessions_by_status[status] = result.scalar() or 0
            
            # Total candidatures aux formations
            total_applications_result = await db.execute(select(func.count(StudentApplication.id)))
            total_applications = total_applications_result.scalar() or 0
            
            # Candidatures par statut
            applications_by_status = {}
            for status in ["RECEIVED", "SUBMITTED", "REFUSED", "APPROVED"]:
                result = await db.execute(
                    select(func.count(StudentApplication.id)).where(StudentApplication.status == status)
                )
                applications_by_status[status] = result.scalar() or 0
            
            # ===== STATISTIQUES SPÉCIALITÉS =====
            total_specialties_result = await db.execute(select(func.count(Specialty.id)))
            total_specialties = total_specialties_result.scalar() or 0
            
            # Formations par spécialité
            trainings_by_specialty_result = await db.execute(
                select(Specialty.name, func.count(Training.id))
                .join(Training, Specialty.id == Training.specialty_id)
                .group_by(Specialty.name)
            )
            trainings_by_specialty = {specialty: count for specialty, count in trainings_by_specialty_result.all()}
            
            # Nouvelles formations ce mois
            new_trainings_this_month_result = await db.execute(
                select(func.count(Training.id)).where(Training.created_at >= this_month_start)
            )
            new_trainings_this_month = new_trainings_this_month_result.scalar() or 0
            
            # Nouvelles sessions ce mois
            new_sessions_this_month_result = await db.execute(
                select(func.count(TrainingSession.id)).where(TrainingSession.created_at >= this_month_start)
            )
            new_sessions_this_month = new_sessions_this_month_result.scalar() or 0
            
        except ImportError:
            # Si les imports échouent, on retourne des valeurs par défaut
            active_trainings = inactive_trainings = 0
            sessions_by_status = {}
            total_applications = 0
            applications_by_status = {}
            total_specialties = 0
            trainings_by_specialty = {}
            new_trainings_this_month = new_sessions_this_month = 0
        
        # ===== STATISTIQUES CENTRES DE FORMATION =====
        try:
            from src.api.system.models import OrganizationCenter
            
            total_centers_result = await db.execute(select(func.count(OrganizationCenter.id)))
            total_centers = total_centers_result.scalar() or 0
            
            # Centres par statut
            centers_by_status = {}
            for status in ["active", "inactive", "suspended", "deleted"]:
                result = await db.execute(
                    select(func.count(OrganizationCenter.id)).where(OrganizationCenter.status == status)
                )
                centers_by_status[status] = result.scalar() or 0
            
            # Centres par type
            centers_by_type_result = await db.execute(
                select(OrganizationCenter.organization_type, func.count(OrganizationCenter.id))
                .group_by(OrganizationCenter.organization_type)
            )
            centers_by_type = {org_type: count for org_type, count in centers_by_type_result.all()}
            
        except ImportError:
            total_centers = 0
            centers_by_status = {}
            centers_by_type = {}
        
        # ===== STATISTIQUES ARTICLES/BLOG =====
        try:
            from src.api.blog.models import Post, PostCategory
            
            total_posts_result = await db.execute(select(func.count(Post.id)))
            total_posts = total_posts_result.scalar() or 0
            
            # Articles publiés vs brouillons
            published_posts_result = await db.execute(
                select(func.count(Post.id)).where(Post.published_at.isnot(None))
            )
            published_posts = published_posts_result.scalar() or 0
            
            draft_posts = total_posts - published_posts
            
            # Articles par catégorie
            posts_by_category_result = await db.execute(
                select(PostCategory.title, func.count(Post.id))
                .join(Post, PostCategory.id == Post.category_id)
                .group_by(PostCategory.title)
            )
            posts_by_category = {category: count for category, count in posts_by_category_result.all()}
            
            # Articles créés ce mois
            posts_this_month_result = await db.execute(
                select(func.count(Post.id)).where(Post.created_at >= this_month_start)
            )
            posts_this_month = posts_this_month_result.scalar() or 0
            
        except ImportError:
            total_posts = published_posts = draft_posts = posts_this_month = 0
            posts_by_category = {}
        
        # ===== STATISTIQUES OFFRES D'EMPLOI =====
        try:
            from src.api.job_offers.models import JobOffer, JobApplication
            
            total_job_offers_result = await db.execute(select(func.count(JobOffer.id)))
            total_job_offers = total_job_offers_result.scalar() or 0
            
            # Offres disponibles vs indisponibles (basé sur la date limite)
            today = datetime.now().date()
            available_offers_result = await db.execute(
                select(func.count(JobOffer.id)).where(JobOffer.submission_deadline >= today)
            )
            available_offers = available_offers_result.scalar() or 0
            
            unavailable_offers = total_job_offers - available_offers
            
            # Offres par type de contrat
            offers_by_contract_result = await db.execute(
                select(JobOffer.contract_type, func.count(JobOffer.id))
                .group_by(JobOffer.contract_type)
            )
            offers_by_contract = {contract_type: count for contract_type, count in offers_by_contract_result.all()}
            
            # Total candidatures aux offres
            total_job_applications_result = await db.execute(select(func.count(JobApplication.id)))
            total_job_applications = total_job_applications_result.scalar() or 0
            
            # Candidatures par statut
            job_applications_by_status = {}
            for status in ["RECEIVED", "REFUSED", "APPROVED"]:
                result = await db.execute(
                    select(func.count(JobApplication.id)).where(JobApplication.status == status)
                )
                job_applications_by_status[status] = result.scalar() or 0
            
            # Nouvelles offres ce mois
            new_job_offers_this_month_result = await db.execute(
                select(func.count(JobOffer.id)).where(JobOffer.created_at >= this_month_start)
            )
            new_job_offers_this_month = new_job_offers_this_month_result.scalar() or 0
            
        except ImportError:
            total_job_offers = available_offers = unavailable_offers = 0
            offers_by_contract = {}
            total_job_applications = 0
            job_applications_by_status = {}
            new_job_offers_this_month = 0
        
        # ===== STATISTIQUES RÉCLAMATIONS =====
        try:
            from src.api.training.models import Reclamation
            
            total_reclamations_result = await db.execute(select(func.count(Reclamation.id)))
            total_reclamations = total_reclamations_result.scalar() or 0
            
            # Réclamations par statut
            reclamations_by_status = {}
            for status in ["NEW", "IN_PROGRESS", "CLOSED"]:
                result = await db.execute(
                    select(func.count(Reclamation.id)).where(Reclamation.status == status)
                )
                reclamations_by_status[status] = result.scalar() or 0
            
            # Réclamations par priorité
            reclamations_by_priority_result = await db.execute(
                select(Reclamation.priority, func.count(Reclamation.id))
                .group_by(Reclamation.priority)
            )
            reclamations_by_priority = {priority: count for priority, count in reclamations_by_priority_result.all()}
            
        except ImportError:
            total_reclamations = 0
            reclamations_by_status = {}
            reclamations_by_priority = {}
        
        # ===== STATISTIQUES PAIEMENTS (SIMPLIFIÉES) =====
        try:
            from src.api.payments.models import Payment, CinetPayPayment
            
            # Total des paiements généraux
            total_payments_result = await db.execute(select(func.count(Payment.id)))
            total_payments = total_payments_result.scalar() or 0
            
            # Total des paiements CinetPay
            total_cinetpay_result = await db.execute(select(func.count(CinetPayPayment.id)))
            total_cinetpay = total_cinetpay_result.scalar() or 0
            
        except ImportError:
            total_payments = 0
            total_cinetpay = 0
        
        return {
            "users": {
                "total": total_users,
                "by_status": users_by_status,
                "by_type": user_types,
                "by_country": users_by_country,
                "two_factor_enabled": two_factor_enabled,
                "new_this_month": new_users_this_month
            },
            "trainings": {
                "total_active": active_trainings,
                "total_inactive": inactive_trainings,
                "sessions_by_status": sessions_by_status,
                "new_this_month": new_trainings_this_month
            },
            "applications": {
                "total_training_applications": total_applications,
                "training_applications_by_status": applications_by_status,
                "total_job_applications": total_job_applications,
                "job_applications_by_status": job_applications_by_status
            },
            "specialties": {
                "total": total_specialties,
                "trainings_by_specialty": trainings_by_specialty
            },
            "centers": {
                "total": total_centers,
                "by_status": centers_by_status,
                "by_type": centers_by_type
            },
            "blog": {
                "total_posts": total_posts,
                "published_posts": published_posts,
                "draft_posts": draft_posts,
                "by_category": posts_by_category,
                "new_this_month": posts_this_month
            },
            "job_offers": {
                "total": total_job_offers,
                "available": available_offers,
                "unavailable": unavailable_offers,
                "by_contract_type": offers_by_contract,
                "new_this_month": new_job_offers_this_month
            },
            "reclamations": {
                "total": total_reclamations,
                "by_status": reclamations_by_status,
                "by_priority": reclamations_by_priority
            },
            "payments": {
                "total_payments": total_payments,
                "total_cinetpay": total_cinetpay
            },
            "sessions": {
                "new_this_month": new_sessions_this_month
            }
        }
        
    except Exception as e:
        # Log l'erreur pour le debugging
        print(f"Erreur dans get_comprehensive_statistics: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Retourner des données par défaut en cas d'erreur
        return {
            "error": "Erreur lors de la récupération des statistiques",
            "message": str(e),
            "users": {
                "total": 0,
                "by_status": {},
                "by_type": {},
                "by_country": {},
                "two_factor_enabled": 0,
                "new_this_month": 0
            },
            "trainings": {
                "total_active": 0,
                "total_inactive": 0,
                "sessions_by_status": {},
                "new_this_month": 0
            },
            "applications": {
                "total_training_applications": 0,
                "training_applications_by_status": {},
                "total_job_applications": 0,
                "job_applications_by_status": {}
            },
            "specialties": {
                "total": 0,
                "trainings_by_specialty": {}
            },
            "centers": {
                "total": 0,
                "by_status": {},
                "by_type": {}
            },
            "blog": {
                "total_posts": 0,
                "published_posts": 0,
                "draft_posts": 0,
                "by_category": {},
                "new_this_month": 0
            },
            "job_offers": {
                "total": 0,
                "available": 0,
                "unavailable": 0,
                "by_contract_type": {},
                "new_this_month": 0
            },
            "reclamations": {
                "total": 0,
                "by_status": {},
                "by_priority": {}
            },
            "payments": {
                "total_payments": 0,
                "total_cinetpay": 0
            },
            "sessions": {
                "new_this_month": 0
            }
        }

@router.get("/payment-stats")
async def get_payment_statistics(
    db: AsyncSession = Depends(get_session_async)
):
    """Récupérer les statistiques détaillées des paiements par module et statut"""
    
    try:
        # ===== STATISTIQUES FORMATIONS DÉTAILLÉES =====
        training_stats = {}
        try:
            from src.api.training.models import StudentApplication
            
            # Statistiques par statut pour les formations
            for status in ["RECEIVED", "SUBMITTED", "REFUSED", "APPROVED"]:
                # Frais d'étude de dossier par statut
                registration_fees_result = await db.execute(
                    select(
                        func.sum(StudentApplication.registration_fee),
                        func.count(StudentApplication.id),
                        func.count(StudentApplication.id).filter(StudentApplication.payment_id.isnot(None)),
                        func.count(StudentApplication.id).filter(StudentApplication.payment_id.is_(None))
                    ).where(StudentApplication.status == status)
                )
                reg_total, reg_count, reg_paid, reg_unpaid = registration_fees_result.first()
                
                # Frais de formation par statut
                training_fees_result = await db.execute(
                    select(
                        func.sum(StudentApplication.training_fee),
                        func.count(StudentApplication.id),
                        func.count(StudentApplication.id).filter(StudentApplication.payment_id.isnot(None)),
                        func.count(StudentApplication.id).filter(StudentApplication.payment_id.is_(None))
                    ).where(StudentApplication.status == status)
                )
                train_total, train_count, train_paid, train_unpaid = training_fees_result.first()
                
                training_stats[status] = {
                    "registration_fees": {
                        "total_amount": float(reg_total or 0),
                        "total_count": reg_count or 0,
                        "paid_count": reg_paid or 0,
                        "unpaid_count": reg_unpaid or 0
                    },
                    "training_fees": {
                        "total_amount": float(train_total or 0),
                        "total_count": train_count or 0,
                        "paid_count": train_paid or 0,
                        "unpaid_count": train_unpaid or 0
                    }
                }
            
        except ImportError:
            training_stats = {}
        
        # ===== STATISTIQUES OFFRES D'EMPLOI DÉTAILLÉES =====
        job_stats = {}
        try:
            from src.api.job_offers.models import JobApplication
            
            # Statistiques par statut pour les offres d'emploi
            for status in ["RECEIVED", "REFUSED", "APPROVED"]:
                # Frais de soumission par statut
                submission_fees_result = await db.execute(
                    select(
                        func.sum(JobApplication.submission_fee),
                        func.count(JobApplication.id),
                        func.count(JobApplication.id).filter(JobApplication.payment_id.isnot(None)),
                        func.count(JobApplication.id).filter(JobApplication.payment_id.is_(None))
                    ).where(JobApplication.status == status)
                )
                sub_total, sub_count, sub_paid, sub_unpaid = submission_fees_result.first()
                
                job_stats[status] = {
                    "submission_fees": {
                        "total_amount": float(sub_total or 0),
                        "total_count": sub_count or 0,
                        "paid_count": sub_paid or 0,
                        "unpaid_count": sub_unpaid or 0
                    }
                }
            
        except ImportError:
            job_stats = {}
        
        # ===== STATISTIQUES GLOBALES CUMULÉES =====
        global_stats = {}
        try:
            from src.api.payments.models import Payment, CinetPayPayment
            
            # Paiements généraux par statut
            for status in ["pending", "accepted", "refused", "cancelled", "error", "rembourse"]:
                # Nombre de paiements par statut
                count_result = await db.execute(
                    select(func.count(Payment.id)).where(Payment.status == status)
                )
                count = count_result.scalar() or 0
                
                # Montants par statut
                amount_result = await db.execute(
                    select(func.sum(Payment.product_amount)).where(Payment.status == status)
                )
                amount = float(amount_result.scalar() or 0)
                
                global_stats[status] = {
                    "count": count,
                    "amount": amount
                }
            
            # CinetPay par statut
            for status in ["pending", "accepted", "refused", "cancelled", "error", "rembourse"]:
                # Nombre de paiements CinetPay par statut
                count_result = await db.execute(
                    select(func.count(CinetPayPayment.id)).where(CinetPayPayment.status == status)
                )
                count = count_result.scalar() or 0
                
                # Montants CinetPay par statut
                amount_result = await db.execute(
                    select(func.sum(CinetPayPayment.amount)).where(CinetPayPayment.status == status)
                )
                amount = float(amount_result.scalar() or 0)
                
                global_stats[f"cinetpay_{status}"] = {
                    "count": count,
                    "amount": amount
                }
            
        except ImportError:
            global_stats = {}
        
        # ===== STATISTIQUES TEMPORELLES =====
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_week_start = datetime.now() - timedelta(days=7)
        
        temporal_stats = {}
        try:
            from src.api.payments.models import Payment, CinetPayPayment
            
            # Paiements généraux ce mois
            payments_this_month_result = await db.execute(
                select(func.count(Payment.id), func.sum(Payment.product_amount))
                .where(Payment.created_at >= this_month_start)
            )
            payments_this_month_count, payments_this_month_amount = payments_this_month_result.first()
            
            # Paiements généraux cette semaine
            payments_this_week_result = await db.execute(
                select(func.count(Payment.id), func.sum(Payment.product_amount))
                .where(Payment.created_at >= this_week_start)
            )
            payments_this_week_count, payments_this_week_amount = payments_this_week_result.first()
            
            # CinetPay ce mois
            cinetpay_this_month_result = await db.execute(
                select(func.count(CinetPayPayment.id), func.sum(CinetPayPayment.amount))
                .where(CinetPayPayment.created_at >= this_month_start)
            )
            cinetpay_this_month_count, cinetpay_this_month_amount = cinetpay_this_month_result.first()
            
            temporal_stats = {
                "general_payments": {
                    "this_month": {
                        "count": payments_this_month_count or 0,
                        "amount": float(payments_this_month_amount or 0)
                    },
                    "this_week": {
                        "count": payments_this_week_count or 0,
                        "amount": float(payments_this_week_amount or 0)
                    }
                },
                "cinetpay_payments": {
                    "this_month": {
                        "count": cinetpay_this_month_count or 0,
                        "amount": float(cinetpay_this_month_amount or 0)
                    }
                }
            }
            
        except ImportError:
            temporal_stats = {}
        
        return {
            "training_payments": training_stats,
            "job_payments": job_stats,
            "global_stats": global_stats,
            "temporal_stats": temporal_stats
        }
        
    except Exception as e:
        # Log l'erreur pour le debugging
        print(f"Erreur dans get_payment_statistics: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Retourner des données par défaut en cas d'erreur
        return {
            "error": "Erreur lors de la récupération des statistiques de paiement",
            "message": str(e),
            "training_payments": {},
            "job_payments": {},
            "global_stats": {},
            "temporal_stats": {}
        }