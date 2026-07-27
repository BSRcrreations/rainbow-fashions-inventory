import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "../../lib/utils";


const buttonVariants = cva(
  "focus-ring inline-flex items-center justify-center gap-2 rounded-lg text-sm font-semibold shadow-sm transition-all duration-200 hover:-translate-y-px disabled:pointer-events-none disabled:translate-y-0 disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary-700 text-white hover:bg-primary-800 hover:shadow-md",
        secondary: "border border-border bg-surface text-slate-700 hover:border-slate-300 hover:bg-surface-subtle hover:shadow-md",
        destructive: "bg-error text-white hover:bg-red-700 hover:shadow-md",
        ghost: "shadow-none text-slate-700 hover:bg-slate-100",
      },
      size: {
        default: "h-control px-5",
        sm: "h-control-sm px-4",
        icon: "h-control-sm w-control-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);


export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}


export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);

Button.displayName = "Button";
