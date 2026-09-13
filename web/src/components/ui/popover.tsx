import * as PopoverPrimitive from '@radix-ui/react-popover'
import { cn } from '@/lib/utils'
import * as React from 'react'

export const Popover = PopoverPrimitive.Root
export const PopoverTrigger = PopoverPrimitive.Trigger

export function PopoverContent({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        sideOffset={6}
        className={cn(
          'z-50 rounded-lg border border-border-strong bg-bg-panel p-2 shadow-sm',
          className
        )}
        {...props}
      />
    </PopoverPrimitive.Portal>
  )
}
