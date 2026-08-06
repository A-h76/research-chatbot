import { WritingOutlineRail } from "./WritingOutlineRail";
import type { WritingSectionType } from "@/features/evidence/hooks/useGroundedWriting";

type VersionItem = {
  id: number;
  version_no: number;
  source: string;
  created_at?: string | null;
  title?: string | null;
  content?: string | null;
};

export function WritingOutlineTab({
  sectionType,
  onSectionTypeChange,
  versions,
  onRestoreVersion,
}: {
  sectionType: WritingSectionType;
  onSectionTypeChange: (next: WritingSectionType) => void;
  versions?: VersionItem[];
  onRestoreVersion?: (versionId: number) => void;
}) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-4">
      <WritingOutlineRail
        sectionType={sectionType}
        onSectionTypeChange={onSectionTypeChange}
        versions={versions}
        onRestoreVersion={onRestoreVersion}
        className="border-0 bg-transparent p-0"
      />
    </div>
  );
}
