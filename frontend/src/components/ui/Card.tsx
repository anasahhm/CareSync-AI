"use client";

import { forwardRef, HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "glass" | "elevated" | "bordered";
  padding?: "none" | "sm" | "md" | "lg";
  glow?: "none" | "blue" | "purple" | "teal";
}

const variantClasses = {
  default: "bg-[#0d0d12] border border-[#1a1a28]",
  glass: "bg-black/40 backdrop-blur-xl border border-white/8",
  elevated: "bg-[#11111a] border border-[#1a1a28] shadow-2xl shadow-black/40",
  bordered: "bg-transparent border border-[#252535] hover:border-[#333348] transition-colors duration-200",
};

const paddingClasses = {
  none: "",
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
};

const glowClasses = {
  none: "",
  blue: "shadow-[0_0_30px_rgba(59,130,246,0.08)]",
  purple: "shadow-[0_0_30px_rgba(139,92,246,0.08)]",
  teal: "shadow-[0_0_30px_rgba(20,184,166,0.08)]",
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = "default", padding = "md", glow = "none", className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl",
        variantClasses[variant],
        paddingClasses[padding],
        glowClasses[glow],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
);
Card.displayName = "Card";

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-1 mb-4", className)} {...props}>
      {children}
    </div>
  )
);
CardHeader.displayName = "CardHeader";

export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, children, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-base font-semibold text-white/90 tracking-tight", className)} {...props}>
      {children}
    </h3>
  )
);
CardTitle.displayName = "CardTitle";

export const CardDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, children, ...props }, ref) => (
    <p ref={ref} className={cn("text-sm text-white/40 leading-relaxed", className)} {...props}>
      {children}
    </p>
  )
);
CardDescription.displayName = "CardDescription";

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn("", className)} {...props}>
      {children}
    </div>
  )
);
CardContent.displayName = "CardContent";

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center gap-3 mt-4 pt-4 border-t border-[#1a1a28]", className)} {...props}>
      {children}
    </div>
  )
);
CardFooter.displayName = "CardFooter";
