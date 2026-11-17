import { useLayoutEffect, useState, type ComponentProps, type CSSProperties, type ReactNode } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

type FormDialogProps = {
  open: boolean;
  onClose: () => void;
  pending: boolean;
  title: string;
  description: string;
  wide?: boolean;
  finalFocus?: ComponentProps<typeof DialogContent>["finalFocus"];
  children: ReactNode;
};

export function FormDialog({
  open,
  onClose,
  pending,
  title,
  description,
  wide = false,
  finalFocus,
  children,
}: FormDialogProps) {
  const [viewportBounds, setViewportBounds] = useState<{ height: number; offsetTop: number }>();

  useLayoutEffect(() => {
    const viewport = window.visualViewport;
    if (!open || !viewport) return;

    const updateViewportBounds = () => {
      // Follow the keyboard's visible area; leave pinch-zoom free to pan normally.
      setViewportBounds(viewport.scale === 1
        ? { height: viewport.height, offsetTop: viewport.offsetTop }
        : undefined);
    };

    updateViewportBounds();
    viewport.addEventListener("resize", updateViewportBounds);
    viewport.addEventListener("scroll", updateViewportBounds);
    return () => {
      viewport.removeEventListener("resize", updateViewportBounds);
      viewport.removeEventListener("scroll", updateViewportBounds);
    };
  }, [open]);

  const viewportStyle = viewportBounds ? {
    "--dialog-viewport-height": `${viewportBounds.height}px`,
    top: `${viewportBounds.offsetTop + viewportBounds.height / 2}px`,
  } as CSSProperties : undefined;
  // Matches the 30rem short-viewport rule in index.css at the default font size.
  const isShortViewport = viewportBounds !== undefined && viewportBounds.height < 480;

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && !pending) onClose();
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        finalFocus={finalFocus}
        style={viewportStyle}
        data-short-viewport={isShortViewport || undefined}
        showCloseButton={!pending}
        className={cn(
          "form-dialog @container/form flex max-h-[calc(var(--dialog-viewport-height,100dvh)-2rem)] flex-col gap-0 overflow-y-auto p-0 [--dialog-width:36rem]",
          wide && "[--dialog-width:42rem]",
        )}
      >
        <DialogHeader className="max-h-[calc(var(--dialog-viewport-height,100dvh)*0.3)] shrink-0 overflow-y-auto border-b p-4 pr-14">
          <DialogTitle className="wrap-anywhere">{title}</DialogTitle>
          <DialogDescription className="wrap-anywhere">{description}</DialogDescription>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}
