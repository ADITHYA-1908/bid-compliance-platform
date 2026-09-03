/**
 * V2 API Client - Enhanced Experimental Features
 * Corresponds to backend/app/api/v2
 */

import { api } from "@/lib/api";
import type {
  TenderSearchFilter,
  TenderWithMatchScore,
  TenderDetailEnhanced,
  TenderAnalysisResult,
  TenderMatchScore,
  ComplianceMatrix,
  ComplianceScore,
  ReadinessScore,
  DocumentChecklist,
  PreSubmissionChecklist,
  BidRiskProfile,
  BidderRiskProfile,
  DocumentQualityCheck,
  EnhancedDocumentVerification,
  DuplicateMatch,
  DocumentFingerprint,
  CertificateValidityStatus,
  Notification,
  NotificationCenter,
  AIMessage,
  AIEligibilityAnalysis,
  AITenderRecommendation,
  AIRecommendation,
  AIAnswerWithEvidence,
} from "@/types/v2";

const V2_BASE_PATH = "/api/v2";

/**
 * V2 API Client for Enhanced Features
 * All V2 endpoints are under /api/v2/
 */
export const apiV2 = {
  /**
   * Tender Discovery & Analysis Endpoints
   */
  tenders: {
    /**
     * Search tenders with advanced filters
     * GET /api/v2/tenders/search
     */
    search: async (filters: TenderSearchFilter): Promise<TenderWithMatchScore[]> => {
      const response = await fetch(`${V2_BASE_PATH}/tenders/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
        body: JSON.stringify(filters),
      });
      if (!response.ok) throw new Error("Tender search failed");
      return response.json();
    },

    /**
     * Get tender with AI analysis and match score
     * GET /api/v2/tenders/{tender_id}/enhanced
     */
    getEnhanced: async (tenderId: string): Promise<TenderDetailEnhanced> => {
      const response = await fetch(`${V2_BASE_PATH}/tenders/${tenderId}/enhanced`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get tender details");
      return response.json();
    },

    /**
     * Analyze tender with AI
     * POST /api/v2/tenders/{tender_id}/analyze
     */
    analyze: async (tenderId: string): Promise<TenderAnalysisResult> => {
      const response = await fetch(`${V2_BASE_PATH}/tenders/${tenderId}/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Tender analysis failed");
      return response.json();
    },

    /**
     * Get AI match score for bidder
     * GET /api/v2/tenders/{tender_id}/match-score/{bidder_id}
     */
    getMatchScore: async (
      tenderId: string,
      bidderId: string
    ): Promise<TenderMatchScore> => {
      const response = await fetch(
        `${V2_BASE_PATH}/tenders/${tenderId}/match-score/${bidderId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to get match score");
      return response.json();
    },

    /**
     * Get recommended tenders for bidder
     * GET /api/v2/tenders/recommendations/{bidder_id}
     */
    getRecommendations: async (bidderId: string): Promise<TenderWithMatchScore[]> => {
      const response = await fetch(
        `${V2_BASE_PATH}/tenders/recommendations/${bidderId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to get recommendations");
      return response.json();
    },
  },

  /**
   * Compliance & Scoring Endpoints
   */
  compliance: {
    /**
     * Get compliance matrix for bid
     * GET /api/v2/compliance/{bid_id}/matrix
     */
    getMatrix: async (bidId: string): Promise<ComplianceMatrix> => {
      const response = await fetch(`${V2_BASE_PATH}/compliance/${bidId}/matrix`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get compliance matrix");
      return response.json();
    },

    /**
     * Get compliance score
     * GET /api/v2/compliance/{bid_id}/score
     */
    getScore: async (bidId: string): Promise<ComplianceScore> => {
      const response = await fetch(`${V2_BASE_PATH}/compliance/${bidId}/score`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get compliance score");
      return response.json();
    },

    /**
     * Get readiness score
     * GET /api/v2/compliance/{bid_id}/readiness
     */
    getReadiness: async (bidId: string): Promise<ReadinessScore> => {
      const response = await fetch(
        `${V2_BASE_PATH}/compliance/${bidId}/readiness`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to get readiness score");
      return response.json();
    },

    /**
     * Get document checklist
     * GET /api/v2/compliance/{bid_id}/checklist
     */
    getChecklist: async (bidId: string): Promise<DocumentChecklist> => {
      const response = await fetch(
        `${V2_BASE_PATH}/compliance/${bidId}/checklist`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to get checklist");
      return response.json();
    },

    /**
     * Run pre-submission checks
     * POST /api/v2/compliance/{bid_id}/pre-submission-check
     */
    preSubmissionCheck: async (bidId: string): Promise<PreSubmissionChecklist> => {
      const response = await fetch(
        `${V2_BASE_PATH}/compliance/${bidId}/pre-submission-check`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Pre-submission check failed");
      return response.json();
    },
  },

  /**
   * Risk Analysis Endpoints
   */
  risk: {
    /**
     * Get bid risk profile
     * GET /api/v2/risk/bid/{bid_id}
     */
    getBidRiskProfile: async (bidId: string): Promise<BidRiskProfile> => {
      const response = await fetch(`${V2_BASE_PATH}/risk/bid/${bidId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get risk profile");
      return response.json();
    },

    /**
     * Get bidder risk profile
     * GET /api/v2/risk/bidder/{bidder_id}
     */
    getBidderRiskProfile: async (bidderId: string): Promise<BidderRiskProfile> => {
      const response = await fetch(`${V2_BASE_PATH}/risk/bidder/${bidderId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get bidder risk profile");
      return response.json();
    },

    /**
     * Detect duplicate documents
     * POST /api/v2/risk/duplicates/detect
     */
    detectDuplicates: async (documentIds: string[]): Promise<DuplicateMatch[]> => {
      const response = await fetch(`${V2_BASE_PATH}/risk/duplicates/detect`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
        body: JSON.stringify({ document_ids: documentIds }),
      });
      if (!response.ok) throw new Error("Duplicate detection failed");
      return response.json();
    },

    /**
     * Get document fingerprint
     * GET /api/v2/risk/fingerprint/{document_id}
     */
    getFingerprint: async (documentId: string): Promise<DocumentFingerprint> => {
      const response = await fetch(`${V2_BASE_PATH}/risk/fingerprint/${documentId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get fingerprint");
      return response.json();
    },

    /**
     * Check certificate validity
     * GET /api/v2/risk/certificate/{certificate_id}/validity
     */
    checkCertificateValidity: async (
      certificateId: string
    ): Promise<CertificateValidityStatus> => {
      const response = await fetch(
        `${V2_BASE_PATH}/risk/certificate/${certificateId}/validity`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Certificate validity check failed");
      return response.json();
    },
  },

  /**
   * Document Management Endpoints
   */
  documents: {
    /**
     * Check document quality
     * POST /api/v2/documents/{document_id}/quality-check
     */
    checkQuality: async (documentId: string): Promise<DocumentQualityCheck> => {
      const response = await fetch(
        `${V2_BASE_PATH}/documents/${documentId}/quality-check`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Quality check failed");
      return response.json();
    },

    /**
     * Verify document with AI
     * POST /api/v2/documents/{document_id}/verify
     */
    verify: async (documentId: string): Promise<EnhancedDocumentVerification> => {
      const response = await fetch(`${V2_BASE_PATH}/documents/${documentId}/verify`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Document verification failed");
      return response.json();
    },
  },

  /**
   * AI Assistant & Copilot Endpoints
   */
  ai: {
    /**
     * Ask AI copilot a question
     * POST /api/v2/ai/ask
     */
    ask: async (question: string, context?: Record<string, any>): Promise<AIMessage> => {
      const response = await fetch(`${V2_BASE_PATH}/ai/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
        body: JSON.stringify({ question, context }),
      });
      if (!response.ok) throw new Error("AI question failed");
      return response.json();
    },

    /**
     * Check eligibility with AI
     * POST /api/v2/ai/eligibility-check
     */
    checkEligibility: async (
      bidderId: string,
      tenderId: string
    ): Promise<AIEligibilityAnalysis> => {
      const response = await fetch(`${V2_BASE_PATH}/ai/eligibility-check`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
        body: JSON.stringify({ bidder_id: bidderId, tender_id: tenderId }),
      });
      if (!response.ok) throw new Error("Eligibility check failed");
      return response.json();
    },

    /**
     * Get AI tender recommendation
     * GET /api/v2/ai/tender-recommendation/{tender_id}/{bidder_id}
     */
    getTenderRecommendation: async (
      tenderId: string,
      bidderId: string
    ): Promise<AITenderRecommendation> => {
      const response = await fetch(
        `${V2_BASE_PATH}/ai/tender-recommendation/${tenderId}/${bidderId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to get recommendation");
      return response.json();
    },

    /**
     * Get AI recommendations
     * GET /api/v2/ai/recommendations/{bidder_id}
     */
    getRecommendations: async (
      bidderId: string
    ): Promise<AIRecommendation[]> => {
      const response = await fetch(`${V2_BASE_PATH}/ai/recommendations/${bidderId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get recommendations");
      return response.json();
    },

    /**
     * Get answer with evidence
     * POST /api/v2/ai/answer-with-evidence
     */
    getAnswerWithEvidence: async (
      question: string
    ): Promise<AIAnswerWithEvidence> => {
      const response = await fetch(`${V2_BASE_PATH}/ai/answer-with-evidence`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
        body: JSON.stringify({ question }),
      });
      if (!response.ok) throw new Error("Failed to get answer with evidence");
      return response.json();
    },
  },

  /**
   * Notification Endpoints
   */
  notifications: {
    /**
     * Get notification center
     * GET /api/v2/notifications/center
     */
    getCenter: async (): Promise<NotificationCenter> => {
      const response = await fetch(`${V2_BASE_PATH}/notifications/center`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to get notifications");
      return response.json();
    },

    /**
     * Mark notification as read
     * PATCH /api/v2/notifications/{notification_id}/read
     */
    markAsRead: async (notificationId: string): Promise<Notification> => {
      const response = await fetch(
        `${V2_BASE_PATH}/notifications/${notificationId}/read`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to mark notification as read");
      return response.json();
    },

    /**
     * Mark all as read
     * PATCH /api/v2/notifications/mark-all-read
     */
    markAllAsRead: async (): Promise<void> => {
      const response = await fetch(
        `${V2_BASE_PATH}/notifications/mark-all-read`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to mark all as read");
    },

    /**
     * Delete notification
     * DELETE /api/v2/notifications/{notification_id}
     */
    delete: async (notificationId: string): Promise<void> => {
      const response = await fetch(
        `${V2_BASE_PATH}/notifications/${notificationId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
          },
        }
      );
      if (!response.ok) throw new Error("Failed to delete notification");
    },
  },

  /**
   * V2 Status
   */
  status: async () => {
    const response = await fetch(`${V2_BASE_PATH}/`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("bidverify_auth_token") || ""}`,
      },
    });
    if (!response.ok) throw new Error("Failed to get V2 status");
    return response.json();
  },
};

export default apiV2;
