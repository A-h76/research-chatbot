/**
 * Paper Workspace phase mappers — stable view models for tabs.
 *
 * mapStructure / mapClassification / mapEntities / mapEvidence
 * (+ mapKnowledgeGraph in M9)
 */

export {
  mapStructure,
  parseDocumentUnderstanding,
  formatQualityScore,
  type DocumentUnderstandingView,
  type DocumentSectionRow,
  type DocumentQualityScores,
} from "./structure";

export {
  DECISION_FAMILIES,
  mapClassification,
  mapAnalysisSummary,
  formatClassificationLabel,
  formatConfidence as formatClassificationConfidence,
  type DecisionFamilyKey,
  type ClassificationDecisionView,
  type CandidateLabelView,
  type AnalysisSummaryView,
  type ClassificationViewModel,
} from "./classification";

export {
  CLINICAL_ENTITY_TYPES,
  mapEntities,
  normalizeEvidence,
  filterEntityItems,
  filterClinicalGroups,
  filterPico,
  formatEntityLabel,
  formatEntityConfidence,
  type ClinicalEntityType,
  type EntityEvidenceView,
  type EntityItemView,
  type ClinicalEntityGroupView,
  type PicoGroupView,
  type EntitiesSummaryView,
  type EntitiesViewModel,
} from "./entities";

export {
  mapEvidence,
  formatConfidence as formatEvidenceConfidence,
  formatLabel as formatEvidenceLabel,
  type EvidenceViewModel,
  type GradeView,
  type FrameworkView,
  type OutcomeGradeView,
  type AssessmentsView,
  type RiskOfBiasView,
  type EvidenceRefView,
} from "./evidence";

export {
  mapKnowledgeGraph,
  filterKnowledgeGraph,
  formatConfidence as formatGraphConfidence,
  formatLabel as formatGraphLabel,
  type KnowledgeGraphViewModel,
  type GraphNodeView,
  type GraphEdgeView,
  type GraphSummaryView,
  type GraphCategory,
} from "./graph";

export {
  mapExplainableChat,
  buildWorkspaceRail,
  workspaceHref,
  groupWorkspaceReferences,
  structureSectionRefId,
  graphNodeRefId,
  resolveGraphNodeId,
  isUsefulStructureHeading,
  type WorkspaceReference,
  type WorkspaceReferenceKind,
  type WorkspaceTab,
  type ExplainableChatViewModel,
  type ChatMessageLike,
  type WorkspaceRailInput,
} from "./chat";
