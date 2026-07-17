import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { SidebarContents } from "@/features/sidebar/components/Sidebar";
import type { Me } from "@/types/api";

export function MobileDrawer({
  me,
  open,
  onOpenChange,
}: {
  me: Me;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-72 bg-sidebar p-0 text-sidebar-foreground">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <SidebarContents me={me} onNavigate={() => onOpenChange(false)} />
      </SheetContent>
    </Sheet>
  );
}
