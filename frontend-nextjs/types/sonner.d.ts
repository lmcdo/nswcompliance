declare module 'sonner' {
  import * as React from 'react';

  export interface ToasterProps {
    theme?: 'light' | 'dark' | 'system';
    className?: string;
    style?: React.CSSProperties;
    [key: string]: any;
  }

  export function Toaster(props: ToasterProps): React.ReactElement;
  export function toast(message: string, options?: any): void;
  export namespace toast {
    function success(message: string, options?: any): void;
    function error(message: string, options?: any): void;
    function info(message: string, options?: any): void;
    function warning(message: string, options?: any): void;
    function loading(message: string, options?: any): void;
    function dismiss(id?: string | number): void;
  }
}
