/**
 * Re-export — canonical component lives in `@/features/pipeline`.
 * @deprecated Import `PipelineStatusPanel` / `isPipelineProcessing` from `@/features/pipeline`.
 */
export {
  PipelineStatusPanel as PipelineStatusCard,
  PipelineStatusPanel,
} from "@/features/pipeline/components/PipelineStatusPanel";
export { isPipelineProcessing } from "@/features/pipeline/isPipelineProcessing";
