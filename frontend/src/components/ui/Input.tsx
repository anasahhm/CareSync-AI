"use client";

import { forwardRef, InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightElement?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, leftIcon, rightElement, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-medium text-white/50 uppercase tracking-wider"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3.5 flex items-center pointer-events-none text-white/30">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={cn(
              "w-full bg-[#0d0d12] border rounded-xl text-sm text-white/90 placeholder:text-white/20",
              "transition-all duration-150 outline-none",
              "focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/10",
              "disabled:opacity-40 disabled:cursor-not-allowed",
              leftIcon ? "pl-10 pr-4 py-3" : "px-4 py-3",
              rightElement ? "pr-12" : "",
              error
                ? "border-red-500/50 focus:border-red-500/70 focus:ring-red-500/10"
                : "border-[#1a1a28] hover:border-[#252535]",
              className
            )}
            {...props}
          />
          {rightElement && (
            <div className="absolute right-3 flex items-center">
              {rightElement}
            </div>
          )}
        </div>
        {error && <p className="text-xs text-red-400 flex items-center gap-1">{error}</p>}
        {hint && !error && <p className="text-xs text-white/30">{hint}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, hint, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium text-white/50 uppercase tracking-wider">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={cn(
            "w-full bg-[#0d0d12] border rounded-xl px-4 py-3 text-sm text-white/90",
            "placeholder:text-white/20 resize-none transition-all duration-150 outline-none",
            "focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/10",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            error
              ? "border-red-500/50 focus:border-red-500/70"
              : "border-[#1a1a28] hover:border-[#252535]",
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
        {hint && !error && <p className="text-xs text-white/30">{hint}</p>}
      </div>
    );
  }
);
Textarea.displayName = "Textarea";
