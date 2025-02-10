import React, { useState } from 'react';
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  CircularProgress,
  Pagination,
  TableFooter,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import axios from 'axios';
import ModelEvaluation from './components/ModelEvaluation';
import MSIScatterPlot from './components/MSIScatterPlot';
import ApiIcon from '@mui/icons-material/Api';

const ITEMS_PER_PAGE = 20;

function App() {
  const [mode, setMode] = useState('state');
  const [stateCode, setStateCode] = useState('');
  const [zipCode, setZipCode] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [showModelEvaluation, setShowModelEvaluation] = useState(false);
  const [apiDocsOpen, setApiDocsOpen] = useState(false);

  const API_URL = process.env.REACT_APP_API_URL + '/api';

  const handleModeChange = (event, newMode) => {
    if (newMode !== null) {
      setMode(newMode);
      setResults(null);
      setError(null);
      setPage(1);
      setShowModelEvaluation(false);
    }
  };

  const handlePageChange = (event, value) => {
    setPage(value);
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (mode === 'state' && stateCode.length === 2) {
      fetchStateData();
    } else if (mode === 'zip' && zipCode.length === 5) {
      fetchZipData();
    }
  };

  const handleStateCodeChange = (event) => {
    setStateCode(event.target.value.toUpperCase());
  };

  const handleStateSearch = () => {
    fetchStateData();
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && stateCode.length === 2) {
      event.preventDefault();
      fetchStateData();
    }
  };

  const fetchStateData = async () => {
    setError(null);
    setResults(null);
    setLoading(true);
    setPage(1);

    try {
      const response = await axios.get(`${API_URL}/recommendations/${stateCode}`);
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchZipData = async () => {
    setError(null);
    setResults(null);
    setLoading(true);
    setPage(1);

    try {
      const response = await axios.get(`${API_URL}/analysis/${zipCode}`);
      setResults(response.data);
    } catch (err) {
      if (err.response?.data?.nearby_zips?.length > 0) {
        const nearbyList = err.response.data.nearby_zips
          .map(zip => `${zip.zip_code} (${zip.city}, ${zip.state})`)
          .join(', ');
        setError(`${err.response.data.error}. However, we found data for these nearby ZIP codes: ${nearbyList}`);
      } else {
        setError(err.response?.data?.error || 'An error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleModelEvaluation = () => {
    setShowModelEvaluation(!showModelEvaluation);
    if (!showModelEvaluation) {
      setResults(null);
      setError(null);
    }
  };

  const handleOpenApiDocs = () => {
    window.open(`${process.env.REACT_APP_API_URL}/swagger/`, '_blank');
  };

  // Utility function to convert data to CSV and trigger download
  const downloadAsCSV = (data, filename) => {
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(header => {
        let cell = row[header];
        // Handle numbers with commas and strings that might contain commas
        if (typeof cell === 'number') {
          return cell.toString();
        }
        cell = cell.toString().replace(/"/g, '""');
        return cell.includes(',') ? `"${cell}"` : cell;
      }).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const renderStateResults = () => {
    if (!results?.recommendations) return null;

    const totalItems = results.recommendations.length;
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    const startIndex = (page - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const currentPageItems = results.recommendations.slice(startIndex, endIndex);

    return (
      <>
        <Alert 
          severity="info" 
          sx={{ 
            mb: 3, 
            '& .MuiAlert-message': { 
              color: '#d32f2f', 
              fontWeight: 'bold',
              fontSize: '1.1rem'
            }
          }}
          icon={<InfoIcon sx={{ color: '#d32f2f' }} />}
        >
          🔍 IMPORTANT: All metrics are provided at the Metropolitan Statistical Area (MSA) level, meaning nearby ZIP codes in the same metro area will share similar values. 📊
        </Alert>

        <MSIScatterPlot stateCode={stateCode} />
        
        <TableContainer component={Paper} sx={{ mt: 3 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Rank</TableCell>
                <TableCell>MSA</TableCell>
                <TableCell>ZIP Code</TableCell>
                <TableCell>City</TableCell>
                <TableCell>Home Value</TableCell>
                <TableCell>Monthly Rent</TableCell>
                <TableCell>Investment Score</TableCell>
                <TableCell>Market Heat</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {currentPageItems.map((item, index) => (
                <TableRow 
                  key={item.zip_code}
                  sx={{ 
                    backgroundColor: item.investment_score > 0.7
                      ? 'rgba(76, 175, 80, 0.1)' 
                      : 'inherit'
                  }}
                >
                  <TableCell>{startIndex + index + 1}</TableCell>
                  <TableCell>{item.region_id}</TableCell>
                  <TableCell>{item.zip_code}</TableCell>
                  <TableCell>{item.city}</TableCell>
                  <TableCell>${item.median_home_value.toLocaleString()}</TableCell>
                  <TableCell>${item.median_rent.toLocaleString()}</TableCell>
                  <TableCell>{(item.investment_score * 100).toFixed(1)}%</TableCell>
                  <TableCell>{item.market_heat.toFixed(1)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 2 }}>
                  <Pagination 
                    count={totalPages} 
                    page={page} 
                    onChange={handlePageChange}
                    color="primary"
                    showFirstButton 
                    showLastButton
                  />
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </TableContainer>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => downloadAsCSV(results.recommendations, `real_estate_data_${stateCode}.csv`)}
            sx={{ mt: 2 }}
          >
            Download Results as CSV
          </Button>
        </Box>
      </>
    );
  };

  const renderZipCodeResults = () => {
    if (!results) return null;

    return (
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {results.city}, {results.state}
          </Typography>
          
          <Alert 
            severity={results.scores.investment_score > 0.7 ? "success" : "info"}
            sx={{ mb: 2 }}
          >
            <Typography variant="subtitle1">
              Investment Score: {(results.scores.investment_score * 100).toFixed(1)}%
            </Typography>
            <Typography variant="body2">
              Ranking Score: {results.scores.ranking_score.toFixed(1)}
            </Typography>
          </Alert>

          <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>Market Metrics</Typography>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableBody>
                <TableRow>
                  <TableCell>Median Home Value</TableCell>
                  <TableCell align="right">${results.metrics.median_home_value.toLocaleString()}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Monthly Rent</TableCell>
                  <TableCell align="right">${results.metrics.median_rent.toLocaleString()}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Price-to-Rent Ratio</TableCell>
                  <TableCell align="right">{results.metrics.price_to_rent.toFixed(2)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Days to Pending</TableCell>
                  <TableCell align="right">{results.metrics.days_pending}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Price Cuts %</TableCell>
                  <TableCell align="right">{results.metrics.price_cuts_percent}%</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Market Heat</TableCell>
                  <TableCell align="right">{results.metrics.market_heat}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
            <Button
              variant="contained"
              color="primary"
              onClick={() => downloadAsCSV([{
                city: results.city,
                state: results.state,
                investment_score: (results.scores.investment_score * 100).toFixed(1) + '%',
                ranking_score: results.scores.ranking_score.toFixed(1),
                median_home_value: results.metrics.median_home_value,
                median_rent: results.metrics.median_rent,
                price_to_rent: results.metrics.price_to_rent,
                days_pending: results.metrics.days_pending,
                price_cuts_percent: results.metrics.price_cuts_percent,
                market_heat: results.metrics.market_heat
              }], `real_estate_data_${zipCode}.csv`)}
              sx={{ mt: 2 }}
            >
              Download Results as CSV
            </Button>
          </Box>
        </CardContent>
      </Card>
    );
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Real Estate Investment Analyzer
        </Typography>

        <Box sx={{ position: 'absolute', top: 20, right: 20 }}>
          <Button
            variant="outlined"
            onClick={handleOpenApiDocs}
            startIcon={<ApiIcon />}
            sx={{ textTransform: 'none' }}
          >
            API Docs
          </Button>
        </Box>

        <Card sx={{ mb: 4, backgroundColor: 'rgba(25, 118, 210, 0.05)', borderRadius: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              How It Works
            </Typography>
            
            <Typography variant="body1" sx={{ mt: 2 }}>
              <ul>
                <li><strong>Investment Score:</strong> A Random Forest Classifier evaluates the investment potential using a weighted scoring system:
                  <ul>
                    <li>Price-to-Rent Ratio (40% weight) - Lower is better, calculated as yearly price / (monthly rent × 12)</li>
                    <li>Market Heat (30% weight) - Higher is better, typically ranges 60-95</li>
                    <li>Days to Pending (15% weight) - Lower is better, typically 10-45 days</li>
                    <li>Price Cuts Percentage (15% weight) - Lower is better, typically 5-25%</li>
                  </ul>
                  Scores above the 60th percentile indicate strong investment potential, placing the property in the top 40% of analyzed locations.
                </li>
                <li><strong>Ranking Score:</strong> Areas are ranked using a separate Random Forest Regressor that considers the relative strength of each metric, 
                with scores ranging from 0-100 to help sort ZIP codes within a state.</li>
              </ul>
            </Typography>

            <Typography variant="subtitle1" color="primary" gutterBottom>
              📊 Key Metrics & Patterns
            </Typography>
            <Typography variant="body2" component="div">
              <ul>
                <li><strong>Price-to-Rent Ratio:</strong> The most critical factor - recommended areas typically show ratios around 18 (vs 40 for not recommended)</li>
                <li><strong>Market Dynamics:</strong> Recommended areas often show:
                  <ul>
                    <li>More moderate home values but higher rental rates</li>
                    <li>Better price stability (lower percentage of price cuts)</li>
                    <li>Strong market heat scores (typically above 77)</li>
                  </ul>
                </li>
              </ul>
            </Typography>

            <Typography variant="subtitle1" color="primary" gutterBottom>
              🔍 Two Ways to Search
            </Typography>
            <Typography variant="body2" component="div">
              <ul>
                <li><strong>State Search:</strong> View all ZIP codes in a state, ranked by my models from highest to lowest investment potential</li>
                <li><strong>ZIP Code Analysis:</strong> Get detailed metrics and scores for a specific location, with suggestions for nearby areas if data isn't available</li>
              </ul>
            </Typography>

            <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic' }}>
              Note: All metrics are provided at the Metropolitan Statistical Area (MSA) level, meaning nearby ZIP codes in the same metro area will share similar values.
            </Typography>
          </CardContent>
        </Card>

        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={handleModeChange}
            aria-label="search mode"
          >
            <ToggleButton value="state" aria-label="state search">
              Search by State
            </ToggleButton>
            <ToggleButton value="zip" aria-label="zip search">
              Search by ZIP
            </ToggleButton>
          </ToggleButtonGroup>

          <Button
            variant="contained"
            color="secondary"
            onClick={toggleModelEvaluation}
            sx={{ ml: 2 }}
          >
            {showModelEvaluation ? 'Back to Search' : 'Model Evaluation'}
          </Button>
        </Box>

        {showModelEvaluation ? (
          <ModelEvaluation />
        ) : (
          <>
            <Card>
              <CardContent>
                <form onSubmit={handleSubmit}>
                  {mode === 'state' ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <TextField
                        label="State Code"
                        value={stateCode}
                        onChange={handleStateCodeChange}
                        onKeyPress={handleKeyPress}
                        inputProps={{ maxLength: 2 }}
                        helperText="Enter a two-letter state code (e.g., MA for Massachusetts)"
                      />
                      <Button 
                        variant="contained" 
                        onClick={handleStateSearch}
                        disabled={stateCode.length !== 2}
                      >
                        Analyze State
                      </Button>
                    </Box>
                  ) : (
                    <TextField
                      fullWidth
                      label="ZIP Code"
                      value={zipCode}
                      onChange={(e) => setZipCode(e.target.value)}
                      margin="normal"
                      required
                      placeholder="e.g., 02108"
                      inputProps={{ maxLength: 5 }}
                      helperText="Enter a 5-digit ZIP code"
                    />
                  )}

                  {mode === 'zip' && (
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
                      <Button 
                        variant="contained" 
                        type="submit"
                        disabled={loading}
                        sx={{ minWidth: 200 }}
                      >
                        {loading ? <CircularProgress size={24} /> : 'Analyze'}
                      </Button>
                    </Box>
                  )}
                </form>
              </CardContent>
            </Card>

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}

            {mode === 'state' ? renderStateResults() : renderZipCodeResults()}
          </>
        )}
      </Box>
    </Container>
  );
}

export default App;
