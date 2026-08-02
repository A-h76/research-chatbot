import { formatQuotaMessage, type QuotaPayload } from "../quotaMessaging";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

/**
 * Clear quota failure / soft-warning panel — never a generic "error".
 */
export function QuotaNotice({
  quota,
  tone = "error",
}: {
  quota: QuotaPayload;
  tone?: "error" | "warning";
}) {
  const navigate = useNavigate();
  const text = formatQuotaMessage(quota);
  return (
    <div
      role="status"
      className={
        tone === "warning"
          ? "rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-[12px] text-amber-950 dark:text-amber-100"
          : "rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-[12px] text-destructive"
      }
    >
      <p className="whitespace-pre-line font-medium leading-relaxed">{text}</p>
      {quota.used != null && quota.limit != null ? (
        <p className="mt-2 tabular-nums text-[11px] opacity-90">
          Used: {quota.used.toLocaleString()} / {quota.limit.toLocaleString()}
          {quota.remaining != null ? ` · Remaining: ${quota.remaining.toLocaleString()}` : ""}
        </p>
      ) : null}
      <div className="mt-2.5 flex flex-wrap gap-2">
        {tone === "error" ? (
          <Button
            size="sm"
            className="h-7 text-[11px]"
            onClick={() => navigate("/settings/account")}
          >
            {quota.upgrade_hint || "Upgrade Plan"}
          </Button>
        ) : null}
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-[11px]"
          onClick={() => navigate(quota.learn_more || "/settings/account")}
        >
          Learn More
        </Button>
      </div>
    </div>
  );
}
