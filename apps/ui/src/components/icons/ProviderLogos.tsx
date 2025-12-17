'use client';

import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: number;
  style?: React.CSSProperties;
}

/**
 * Google Gemini Logo
 * Based on the official Gemini star icon
 */
export function GeminiLogo({ className, size = 24, style }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(className)}
      style={style}
    >
      <defs>
        <linearGradient id="gemini-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4285F4" />
          <stop offset="50%" stopColor="#9B72CB" />
          <stop offset="100%" stopColor="#D96570" />
        </linearGradient>
      </defs>
      <path
        d="M12 2C12 2 12 12 12 12C12 12 2 12 2 12C2 12 12 12 12 12C12 12 12 22 12 22C12 22 12 12 12 12C12 12 22 12 22 12C22 12 12 12 12 12C12 12 12 2 12 2Z"
        fill="url(#gemini-gradient)"
      />
      <ellipse cx="12" cy="12" rx="10" ry="10" fill="url(#gemini-gradient)" opacity="0.2" />
      <path
        d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12"
        stroke="url(#gemini-gradient)"
        strokeWidth="0"
        fill="none"
      />
      <path
        d="M12 3C12.5 7 17 11.5 21 12C17 12.5 12.5 17 12 21C11.5 17 7 12.5 3 12C7 11.5 11.5 7 12 3Z"
        fill="url(#gemini-gradient)"
      />
    </svg>
  );
}

/**
 * OpenAI Logo
 * Official OpenAI hexagon logo
 */
export function OpenAILogo({ className, size = 24, style }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(className)}
      style={style}
    >
      <path
        d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.8956zm16.0993 3.8558L12.6 8.3829l2.02-1.1638a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z"
        fill="#10A37F"
      />
    </svg>
  );
}

/**
 * Anthropic Claude Logo
 * Based on official Anthropic branding
 */
export function AnthropicLogo({ className, size = 24, style }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(className)}
      style={style}
    >
      <path
        d="M17.3037 3.84375H14.2969L19.5469 20.1562H22.5537L17.3037 3.84375Z"
        fill="#D97757"
      />
      <path
        d="M6.69629 3.84375L1.44629 20.1562H4.53223L5.60254 16.875H11.6045L12.6748 20.1562H15.7607L10.5107 3.84375H6.69629ZM6.46973 14.1562L8.60352 7.59375L10.7373 14.1562H6.46973Z"
        fill="#D97757"
      />
    </svg>
  );
}

/**
 * Provider logo component that renders the appropriate logo based on platform
 */
export function ProviderLogo({
  platform,
  className,
  size = 24,
}: {
  platform: 'gemini' | 'openai' | 'anthropic';
  className?: string;
  size?: number;
}) {
  switch (platform) {
    case 'gemini':
      return <GeminiLogo className={className} size={size} />;
    case 'openai':
      return <OpenAILogo className={className} size={size} />;
    case 'anthropic':
      return <AnthropicLogo className={className} size={size} />;
    default:
      return null;
  }
}
