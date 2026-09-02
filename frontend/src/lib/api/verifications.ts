import {
  api,
  BidVerificationListResponse,
  DocumentVerificationListResponse,
  VerificationRecord,
  VerificationRetryResponse,
  VerificationSummaryItem,
  VerificationTriggerResponse,
} from "@/lib/api";

export async function verifyDocumentClaims(
  bidId: string,
  documentId: string
): Promise<VerificationTriggerResponse> {
  return api.verifyDocumentClaims(bidId, documentId);
}

export async function getDocumentVerifications(
  bidId: string,
  documentId: string
): Promise<DocumentVerificationListResponse> {
  return api.getDocumentVerifications(bidId, documentId);
}

export async function getBidVerifications(
  bidId: string
): Promise<BidVerificationListResponse> {
  return api.getBidVerifications(bidId);
}

export async function retryVerification(
  bidId: string,
  verificationId: string
): Promise<VerificationRetryResponse> {
  return api.retryVerification(bidId, verificationId);
}
