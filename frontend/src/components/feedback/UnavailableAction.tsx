import { useId, useState, type ReactElement, type ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const unavailableMessage = "This feature isn't implemented just yet.";

type UnavailableActionProps = {
  render: ReactElement<{ id?: string }>;
  children: ReactNode;
  message?: string;
  side?: "top" | "right";
};

/** Lets unavailable buttons explain themselves on hover, focus, or tap. */
export function UnavailableAction({ render, children, message = unavailableMessage, side = "top" }: UnavailableActionProps) {
  const generatedId = useId();
  const triggerId = render.props.id ?? generatedId;
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen} triggerId={triggerId}>
      <TooltipTrigger
        id={triggerId}
        render={render}
        type="button"
        // Keep the trigger focusable and clickable so it can explain the disabled action.
        aria-disabled="true"
        aria-description={message}
        closeOnClick={false}
        onClick={() => setOpen(true)}
      >
        {children}
      </TooltipTrigger>
      {/* On a narrow screen the popup must not sit above the trigger and take the next tap. */}
      <TooltipContent role="tooltip" side={side} positionerClassName="max-md:pointer-events-none">
        {message}
      </TooltipContent>
    </Tooltip>
  );
}
