from fastapi import APIRouter
from app.api.v1.roles import router as roles_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bidder import router as bidder_router
from app.api.v1.procurement import router as procurement_router
from app.api.v1.admin import router as admin_router
from app.api.v1.tenders import router as tenders_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.validation import router as validation_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.bidder.certificates import router as bidder_certificates_router
from app.api.v1.procurement.certificates import router as procurement_certificates_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(roles_router, prefix="/roles", tags=["Roles"])
api_v1_router.include_router(tenders_router, prefix="/tenders", tags=["Tender Management"])
api_v1_router.include_router(bidder_router, prefix="/bidder", tags=["Bidder"])
api_v1_router.include_router(procurement_router, prefix="/procurement", tags=["Procurement"])
api_v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_v1_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_v1_router.include_router(validation_router, prefix="/admin/validation", tags=["Validation & Benchmarking"])
api_v1_router.include_router(analytics_router, prefix="/procurement/analytics", tags=["Procurement Analytics & Impact"])
api_v1_router.include_router(bidder_certificates_router, prefix="/bidder/certificates", tags=["Bidder Certificate Validity"])
api_v1_router.include_router(procurement_certificates_router, prefix="/procurement/certificates", tags=["Procurement Certificate Validity"])
