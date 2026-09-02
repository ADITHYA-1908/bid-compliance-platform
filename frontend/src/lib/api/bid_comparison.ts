import { api } from "@/lib/api";
import {
  BidComparisonResponse,
  ShortlistRecordResponse,
} from "@/types/bid_comparison";

/**
 * Executes a side-by-side comparative analysis of 2 to 5 submitted bids for a tender.
 */
export async function compareTenderBids(
  tenderId: string,
  bidIds: string[]
): Promise<BidComparisonResponse> {
  return await api.post<BidComparisonResponse>(
    `/procurement/tenders/${tenderId}/compare-bids`,
    {
      bid_ids: bidIds,
    }
  );
}

/**
 * Adds a submitted bid to the shortlist for further review by the procurement officer.
 */
export async function addBidToShortlist(
  tenderId: string,
  bidId: string,
  reason?: string
): Promise<ShortlistRecordResponse> {
  return await api.post<ShortlistRecordResponse>(
    `/procurement/tenders/${tenderId}/bids/${bidId}/shortlist`,
    {
      reason: reason || undefined,
    }
  );
}

/**
 * Removes a submitted bid from the shortlist.
 */
export async function removeBidFromShortlist(
  tenderId: string,
  bidId: string,
  reason?: string
): Promise<ShortlistRecordResponse> {
  const url = `/procurement/tenders/${tenderId}/bids/${bidId}/shortlist${
    reason ? `?reason=${encodeURIComponent(reason)}` : ""
  }`;
  return await api.delete<ShortlistRecordResponse>(url);
}

/**
 * Retrieves all currently shortlisted bids for a tender.
 */
export async function getTenderShortlists(
  tenderId: string
): Promise<ShortlistRecordResponse[]> {
  return await api.get<ShortlistRecordResponse[]>(
    `/procurement/tenders/${tenderId}/shortlists`
  );
}
