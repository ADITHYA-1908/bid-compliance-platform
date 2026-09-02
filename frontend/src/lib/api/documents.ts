import {
  api,
  DocumentProcessing,
  DocumentProcessTriggerResponse,
  DocumentExtractedTextResponse,
  DocumentClassificationResponse,
  DocumentExtractedDataResponse,
  ExtractedFieldItem,
} from "@/lib/api";

export async function getDocumentProcessingStatus(
  bidId: string,
  documentId: string
): Promise<DocumentProcessing> {
  return api.getDocumentProcessing(bidId, documentId);
}

export async function queueDocumentProcessing(
  bidId: string,
  documentId: string
): Promise<DocumentProcessTriggerResponse> {
  return api.processDocument(bidId, documentId);
}

export async function retryDocumentProcessing(
  bidId: string,
  documentId: string
): Promise<DocumentProcessTriggerResponse> {
  return api.retryDocumentProcessing(bidId, documentId);
}

export async function getDocumentExtractedText(
  bidId: string,
  documentId: string
): Promise<DocumentExtractedTextResponse> {
  return api.getDocumentExtractedText(bidId, documentId);
}

export async function getDocumentClassification(
  bidId: string,
  documentId: string
): Promise<DocumentClassificationResponse> {
  return api.getDocumentClassification(bidId, documentId);
}

export async function getDocumentExtractedData(
  bidId: string,
  documentId: string
): Promise<DocumentExtractedDataResponse> {
  return api.getDocumentExtractedData(bidId, documentId);
}


