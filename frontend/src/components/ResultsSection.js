// src/components/ResultsSection.js
import { Box, Typography, Grid, Chip, Paper } from "@mui/material";

export default function ResultsSection({
  originalFile,
  redactedOutput,
  outputType,
  riskScore,
  explanations,
}) {
  const riskColor = riskScore > 70 ? "error" : riskScore > 40 ? "warning" : "success";
  const riskLabel = riskScore > 70 ? "High Risk" : riskScore > 40 ? "Medium Risk" : "Low Risk";

  return (
    <Paper
      elevation={6}
      sx={{
        p: { xs: 3, md: 5 },
        bgcolor: 'background.paper',
        borderRadius: 4,
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography variant="h5" gutterBottom align="center" sx={{ mb: 4 }}>
        Privacy Protection Results
      </Typography>

      <Grid container spacing={4}>
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Original File
          </Typography>
          {outputType === "pdf" ? (
            <iframe
              title="Original PDF preview"
              src={originalFile}
              style={{ width: '100%', height: '500px', borderRadius: 12, border: '1px solid' }}
            />
          ) : (
            <Box
              component="img"
              src={originalFile}
              alt="Original"
              sx={{
                width: '100%',
                borderRadius: 3,
                boxShadow: 3,
                objectFit: 'cover',
              }}
            />
          )}
        </Grid>

        <Grid item xs={12} md={6}>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Redacted & Protected
          </Typography>
          {outputType === "pdf" ? (
            <iframe
              title="Redacted PDF preview"
              src={redactedOutput}
              style={{ width: '100%', height: '500px', borderRadius: 12, border: '1px solid' }}
            />
          ) : (
            <Box
              component="img"
              src={redactedOutput}
              alt="Redacted"
              sx={{
                width: '100%',
                borderRadius: 3,
                boxShadow: 3,
                objectFit: 'cover',
              }}
            />
          )}
        </Grid>
      </Grid>

      <Box sx={{ mt: 5, textAlign: 'center' }}>
        <Chip
          label={`${riskLabel} (${riskScore})`}
          color={riskColor}
          size="large"
          sx={{ fontSize: '1.1rem', px: 3, py: 2.5 }}
        />

        {explanations.length > 0 && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="subtitle1" gutterBottom>
              Detected Privacy Risks:
            </Typography>
            {explanations.map((exp, i) => (
              <Typography key={i} variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                • {exp}
              </Typography>
            ))}
          </Box>
        )}
      </Box>
    </Paper>
  );
}