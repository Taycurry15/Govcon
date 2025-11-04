/**
 * Apple-inspired Card Component
 */

import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

interface CardProps extends HTMLMotionProps<'div'> {
  elevated?: boolean;
  hoverable?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      elevated = false,
      hoverable = false,
      padding = 'md',
      children,
      className = '',
      ...props
    },
    ref
  ) => {
    const baseClasses = 'bg-white rounded-xl transition-all duration-250';

    const shadowClasses = elevated
      ? 'shadow-lg'
      : 'shadow-sm border border-gray-200';

    const hoverClasses = hoverable
      ? 'hover:shadow-xl hover:-translate-y-0.5 cursor-pointer'
      : '';

    const paddingClasses = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    };

    const combinedClasses = `
      ${baseClasses}
      ${shadowClasses}
      ${hoverClasses}
      ${paddingClasses[padding]}
      ${className}
    `.trim().replace(/\s+/g, ' ');

    return (
      <motion.div
        ref={ref}
        className={combinedClasses}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

Card.displayName = 'Card';

export default Card;
