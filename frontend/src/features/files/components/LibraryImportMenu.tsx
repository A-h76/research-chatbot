import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, FileUp, Hash } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { libraryBridgeApi } from "../libraryBridgeApi";
import {
  BibtexIcon,
  MendeleyIcon,
  OpenAlexIcon,
  RisIcon,
  ZoteroIcon,
} from "@/features/sidebar/components/BrandIcons";
import { cn } from "@/lib/utils";

/**
 * Progressive disclosure for Library imports — one menu instead of six equal CTAs.
 */
export function LibraryImportMenu({
  onUpload,
  onBibtex,
  onZoteroImport,
  onMendeleyImport,
  onGoogleDriveImport,
  onDropboxImport,
  onOneDriveImport,
}: {
  onUpload: () => void;
  onBibtex?: () => void;
  onZoteroImport?: () => void;
  onMendeleyImport?: () => void;
  onGoogleDriveImport?: () => void;
  onDropboxImport?: () => void;
  onOneDriveImport?: () => void;
}) {
  const navigate = useNavigate();
  const { data: connections } = useQuery({
    queryKey: ["library-connections"],
    queryFn: libraryBridgeApi.connections,
  });
  const zoteroOn = Boolean(connections?.zotero?.connected);
  const mendeleyOn = Boolean(connections?.mendeley?.connected);
  const driveOn = Boolean(connections?.google_drive?.connected);
  const dropboxOn = Boolean(connections?.dropbox?.connected);
  const onedriveOn = Boolean(connections?.onedrive?.connected);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 text-[12px] font-medium",
          "text-foreground transition-colors hover:bg-muted",
        )}
      >
        Import
        <ChevronDown className="size-3.5 opacity-70" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-52">
        <DropdownMenuItem onClick={onUpload}>
          <FileUp className="size-3.5" />
          Upload PDF
        </DropdownMenuItem>
        {onBibtex ? (
          <DropdownMenuItem onClick={onBibtex}>
            <span className="inline-flex items-center gap-0.5">
              <BibtexIcon className="size-3.5" />
              <RisIcon className="size-3.5" />
            </span>
            BibTeX / RIS
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuSeparator />
        {zoteroOn ? (
          <DropdownMenuItem onClick={() => onZoteroImport?.()}>
            <ZoteroIcon className="size-3.5" />
            From Zotero
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem
            onClick={() => void navigate("/settings/integrations")}
          >
            <ZoteroIcon className="size-3.5" />
            Connect Zotero in Integrations
          </DropdownMenuItem>
        )}
        {mendeleyOn ? (
          <DropdownMenuItem onClick={() => onMendeleyImport?.()}>
            <MendeleyIcon className="size-3.5" />
            From Mendeley
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem
            onClick={() => void navigate("/settings/integrations")}
          >
            <MendeleyIcon className="size-3.5" />
            Connect Mendeley in Integrations
          </DropdownMenuItem>
        )}
        {driveOn ? (
          <DropdownMenuItem onClick={() => onGoogleDriveImport?.()}>
            <FileUp className="size-3.5" />
            From Google Drive
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem
            onClick={() => void navigate("/settings/integrations")}
          >
            <FileUp className="size-3.5" />
            Connect Google Drive in Integrations
          </DropdownMenuItem>
        )}
        {dropboxOn ? (
          <DropdownMenuItem onClick={() => onDropboxImport?.()}>
            <FileUp className="size-3.5" />
            From Dropbox
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem
            onClick={() => void navigate("/settings/integrations")}
          >
            <FileUp className="size-3.5" />
            Connect Dropbox in Integrations
          </DropdownMenuItem>
        )}
        {onedriveOn ? (
          <DropdownMenuItem onClick={() => onOneDriveImport?.()}>
            <FileUp className="size-3.5" />
            From OneDrive
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem
            onClick={() => void navigate("/settings/integrations")}
          >
            <FileUp className="size-3.5" />
            Connect OneDrive in Integrations
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => void navigate("/search?mode=discover&q=10.")}>
          <OpenAlexIcon className="size-3.5" />
          Import DOI
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => void navigate("/search?mode=discover&provider=pubmed")}>
          <Hash className="size-3.5" />
          Import PMID
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => void navigate("/search?mode=discover&provider=arxiv")}>
          <Hash className="size-3.5" />
          Import arXiv
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => void navigate("/search?mode=discover&provider=europe_pmc")}
        >
          <Hash className="size-3.5" />
          Import Europe PMC
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => void navigate("/search?mode=discover&provider=orcid")}>
          <Hash className="size-3.5" />
          Import ORCID
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
