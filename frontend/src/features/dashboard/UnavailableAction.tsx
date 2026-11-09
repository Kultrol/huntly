import { useId, useState, type ReactElement, type ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const unavailableMessage = "This feature isn't implemented just yet.";

type UnavailableActionProps = {
  render: ReactElement;
  children: ReactNode;
  side?: "top" | "right";
};

/** Lets unavailable buttons explain themselves on hover, focus, or tap. */
export function UnavailableAction({ render, children, side = "top" }: UnavailableActionProps) {
  const triggerId = useId();
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen} triggerId={triggerId}>
      <TooltipTrigger
        id={triggerId}
        render={render}
        type="button"
        // Keep the trigger focusable and clickable so it can explain the disabled action.
        aria-disabled="true"
        aria-description={unavailableMessage}
        closeOnClick={false}
        onClick={() => setOpen(true)}
      >
        {children}
      </TooltipTrigger>
      {/* On a narrow screen the popup must not sit above the trigger and take the next tap. */}
      <TooltipContent role="tooltip" side={side} positionerClassName="max-md:pointer-events-none">
        {unavailableMessage}
      </TooltipContent>
    </Tooltip>
  );
}
