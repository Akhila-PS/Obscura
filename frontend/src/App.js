// src/App.js - Integrated version with routing
import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ThemeProvider, createTheme, CssBaseline } from "@mui/material";

import LandingPage from "./components/LandingPage";
import SensitiveRedaction from "./components/SensitiveRedaction";
import MetadataRedaction from "./components/MetadataRedaction";

function App() {
  const [mode, setMode] = useState('dark');

  const theme = createTheme({
    palette: {
      mode: mode,
      primary: {
        main: '#3B82F6',
        light: '#60A5FA',
        dark: '#2563EB',
      },
      secondary: {
        main: '#22c55e',
      },
      background: {
        default: mode === 'dark' ? '#0f172a' : '#f8fafc',
        paper: mode === 'dark' ? '#1e293b' : '#ffffff',
      },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    },
  });

  const toggleColorMode = () => {
    setMode((prevMode) => (prevMode === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route 
            path="/sensitive-redaction" 
            element={<SensitiveRedaction mode={mode} toggleColorMode={toggleColorMode} />} 
          />
          <Route 
            path="/metadata-redaction" 
            element={<MetadataRedaction />} 
          />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;