import React, { useState, useMemo, createContext, useContext } from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

const ColorModeContext = createContext({ toggleColorMode: () => {} });

export const useColorMode = () => useContext(ColorModeContext);

function Root() {
  const [mode, setMode] = useState('dark'); // default dark for privacy app feel

  const colorMode = useMemo(
    () => ({
      toggleColorMode: () => {
        setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
      },
    }),
    []
  );

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: {
            main: mode === 'dark' ? '#60A5FA' : '#2563EB', // blue-400 / blue-600
          },
          background: {
            default: mode === 'dark' ? '#0F172A' : '#F8FAFC', // slate-900 / slate-50
            paper: mode === 'dark' ? '#1E293B' : '#FFFFFF',   // slate-800 / white
          },
          text: {
            primary: mode === 'dark' ? '#E2E8F0' : '#0F172A',
            secondary: mode === 'dark' ? '#94A3B8' : '#475569',
          },
          success: { main: '#22C55E' },
          warning: { main: '#F59E0B' },
          error: { main: '#EF4444' },
          divider: mode === 'dark' ? '#334155' : '#E2E8F0',
        },
        typography: {
          fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
          h4: { fontWeight: 700, letterSpacing: '-0.5px' },
          h5: { fontWeight: 600 },
          subtitle1: { fontWeight: 500, color: 'text.secondary' },
        },
        shape: { borderRadius: 16 },
        components: {
          MuiButton: {
            styleOverrides: {
              root: {
                textTransform: 'none',
                fontWeight: 600,
                borderRadius: 12,
                padding: '10px 24px',
              },
            },
          },
          MuiCard: {
            styleOverrides: {
              root: {
                backgroundImage: 'none',
                boxShadow: mode === 'dark' 
                  ? '0 10px 30px rgba(0,0,0,0.4)' 
                  : '0 10px 30px rgba(0,0,0,0.08)',
              },
            },
          },
        },
      }),
    [mode]
  );

  return (
    <ColorModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);