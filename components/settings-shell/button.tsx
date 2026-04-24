import type { ReactNode } from "react";

import { Icon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const variants = {
  primary:
    "default",
  secondary:
    "outline",
  ghost:
    "ghost",
  danger:
    "destructive",
} as const;

export function GlanceButton({
  children,
  icon,
  variant = "secondary",
  disabled,
  className,
  ariaLabel,
  onClick,
}: {
  children?: ReactNode;
  icon?: string;
  variant?: keyof typeof variants;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
  onClick?: () => void | Promise<void>;
}) {
  return (
    <Button
      type="button"
      variant={variants[variant]}
      size={children ? "default" : "icon"}
      className={cn("shrink-0 rounded-xl", className)}
      disabled={disabled}
      aria-label={ariaLabel}
      onClick={() => void onClick?.()}
    >
      {icon ? <Icon name={icon} className="size-4" /> : null}
      {children}
    </Button>
  );
}
