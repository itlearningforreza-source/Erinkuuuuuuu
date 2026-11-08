import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@erin/ui-core': path.resolve(__dirname, '../packages/ui-core/src'),
      '@erin/shared-types': path.resolve(__dirname, '../../packages/shared-types/src'),
    },
  },
  build: {
    target: 'es2022',
    minify: 'esbuild',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-tauri': ['@tauri-apps/api', '@tauri-apps/plugin-dialog', '@tauri-apps/plugin-fs', '@tauri-apps/plugin-shell', '@tauri-apps/plugin-http', '@tauri-apps/plugin-store', '@tauri-apps/plugin-clipboard-manager', '@tauri-apps/plugin-global-shortcut', '@tauri-apps/plugin-window-state', '@tauri-apps/plugin-positioner', '@tauri-apps/plugin-opener', '@tauri-apps/plugin-log', '@tauri-apps/plugin-process', '@tauri-apps/plugin-sql'],
          'vendor-radix': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-select', '@radix-ui/react-tabs', '@radix-ui/react-tooltip', '@radix-ui/react-popover', '@radix-ui/react-hover-card', '@radix-ui/react-context-menu', '@radix-ui/react-menubar', '@radix-ui/react-navigation-menu', '@radix-ui/react-scroll-area', '@radix-ui/react-separator', '@radix-ui/react-slider', '@radix-ui/react-switch', '@radix-ui/react-toggle', '@radix-ui/react-toggle-group', '@radix-ui/react-accordion', '@radix-ui/react-collapsible', '@radix-ui/react-label', '@radix-ui/react-radio-group', '@radix-ui/react-checkbox', '@radix-ui/react-progress', '@radix-ui/react-slot', '@radix-ui/react-visually-hidden', '@radix-ui/react-icons'],
          'vendor-charts': ['lightweight-charts'],
          'vendor-state': ['@tanstack/react-query', 'zustand', 'jotai'],
          'vendor-forms': ['react-hook-form', '@hookform/resolvers', 'zod'],
          'vendor-utils': ['date-fns', 'date-fns-tz', 'decimal.js', 'lodash-es', 'clsx', 'tailwind-merge', 'class-variance-authority'],
          'vendor-animation': ['framer-motion'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  server: {
    port: 1420,
    strictPort: true,
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: 1421,
    },
  },
  preview: {
    port: 1420,
    strictPort: true,
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@tauri-apps/api',
      '@tanstack/react-query',
      'zustand',
      'jotai',
      'lightweight-charts',
      'zod',
      'date-fns',
      'decimal.js',
      'lodash-es',
      'clsx',
      'tailwind-merge',
      'class-variance-authority',
      'cmdk',
      'framer-motion',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-select',
      '@radix-ui/react-tabs',
      '@radix-ui/react-tooltip',
      '@radix-ui/react-popover',
      '@radix-ui/react-hover-card',
      '@radix-ui/react-context-menu',
      '@radix-ui/react-menubar',
      '@radix-ui/react-navigation-menu',
      '@radix-ui/react-scroll-area',
      '@radix-ui/react-separator',
      '@radix-ui/react-slider',
      '@radix-ui/react-switch',
      '@radix-ui/react-toggle',
      '@radix-ui/react-toggle-group',
      '@radix-ui/react-accordion',
      '@radix-ui/react-collapsible',
      '@radix-ui/react-label',
      '@radix-ui/react-radio-group',
      '@radix-ui/react-checkbox',
      '@radix-ui/react-progress',
      '@radix-ui/react-slot',
      '@radix-ui/react-visually-hidden',
      '@radix-ui/react-icons',
      'lucide-react',
      'framer-motion',
      'lightweight-charts',
    ],
  },
  esbuild: {
    logOverride: { 'this-is-undefined-in-esm': 'silent' },
  },
});