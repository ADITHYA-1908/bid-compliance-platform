/**
 * API client for Part 8E: Procurement Evaluation Reports & PDF Exports
 */

import { api, API_BASE_URL, getStoredToken } from '@/lib/api';
import {
  BidEvaluationReportResponse,
  TenderReportResponse,
} from '@/types/procurement_report';

export async function getTenderReport(
  tenderId: string
): Promise<TenderReportResponse> {
  return await api.get<TenderReportResponse>(
    `/procurement/tenders/${tenderId}/report`
  );
}

export async function getBidEvaluationReport(
  tenderId: string,
  bidId: string
): Promise<BidEvaluationReportResponse> {
  return await api.get<BidEvaluationReportResponse>(
    `/procurement/tenders/${tenderId}/bids/${bidId}/report`
  );
}

export async function downloadTenderReportPDF(
  tenderId: string
): Promise<{ blob: Blob; filename: string }> {
  const token = getStoredToken();
  const url = `${API_BASE_URL}/api/v1/procurement/tenders/${tenderId}/report/pdf`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    throw new Error(`Failed to download Tender Report PDF (HTTP ${res.status})`);
  }

  const disposition = res.headers.get('content-disposition');
  let filename = `tender_evaluation_summary_${tenderId}.pdf`;
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename=["']?([^"';]+)["']?/);
    if (match && match[1]) filename = match[1];
  }

  const blob = await res.blob();
  return { blob, filename };
}

export async function downloadBidReportPDF(
  tenderId: string,
  bidId: string
): Promise<{ blob: Blob; filename: string }> {
  const token = getStoredToken();
  const url = `${API_BASE_URL}/api/v1/procurement/tenders/${tenderId}/bids/${bidId}/report/pdf`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    throw new Error(`Failed to download Bid Dossier PDF (HTTP ${res.status})`);
  }

  const disposition = res.headers.get('content-disposition');
  let filename = `bid_evaluation_dossier_${bidId}.pdf`;
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename=["']?([^"';]+)["']?/);
    if (match && match[1]) filename = match[1];
  }

  const blob = await res.blob();
  return { blob, filename };
}
