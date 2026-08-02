/** Shared user-facing API failure copy (quota + feature flags). */

import { ApiError } from "@/lib/apiClient";
import {
  formatQuotaMessage,
  quotaFromApiError,
  type QuotaPayload,
} from "@/features/settings/quotaMessaging";

export type { QuotaPayload };
export { formatQuotaMessage, quotaFromApiError };

const FEATURE_DISABLED_MSG = "This feature is temporarily off.";

export function isFeatureDisabledError(err: unknown): boolean {
  if (err instanceof ApiError) {
    return err.code === "feature_disabled" || err.message === "feature_disabled";
  }
  if (err instanceof Error) {
    return err.message === "feature_disabled";
  }
  if (err && typeof err === "object" && "error" in err) {
    return String((err as { error: unknown }).error) === "feature_disabled";
  }
  return false;
}

/** Prefer structured quota / feature_disabled copy over raw API codes. */
export function formatApiFailure(err: unknown, fallback = "Request failed"): string {
  if (isFeatureDisabledError(err)) return FEATURE_DISABLED_MSG;
  if (err instanceof ApiError && err.quota) {
    return formatQuotaMessage(err.quota, err.message || fallback);
  }
  if (err instanceof ApiError) {
    const fromBody = quotaFromApiError(err.body);
    if (fromBody) return formatQuotaMessage(fromBody, err.message || fallback);
    if (err.message && err.message !== "request_failed") return err.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export function quotaFromUnknown(err: unknown): QuotaPayload | null {
  if (err instanceof ApiError) {
    return err.quota ?? quotaFromApiError(err.body);
  }
  if (err && typeof err === "object") {
    return quotaFromApiError(err);
  }
  return null;
}
