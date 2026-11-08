import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private refreshTokenPromise: Promise<string> | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('erin_access_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const newToken = await this.refreshAccessToken();
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
            }
            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed, redirect to login
            localStorage.removeItem('erin_access_token');
            localStorage.removeItem('erin_refresh_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private async refreshAccessToken(): Promise<string> {
    if (this.refreshTokenPromise) {
      return this.refreshTokenPromise;
    }

    const refreshToken = localStorage.getItem('erin_refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    this.refreshTokenPromise = (async () => {
      try {
        const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token } = response.data;
        localStorage.setItem('erin_access_token', access_token);
        localStorage.setItem('erin_refresh_token', refresh_token);
        return access_token;
      } finally {
        this.refreshTokenPromise = null;
      }
    })();

    return this.refreshTokenPromise;
  }

  // Auth methods
  async login(username: string, password: string, mfaCode?: string) {
    const response = await this.client.post('/api/v1/auth/login', {
      username,
      password,
      mfa_code: mfaCode,
    });
    const { access_token, refresh_token } = response.data;
    localStorage.setItem('erin_access_token', access_token);
    localStorage.setItem('erin_refresh_token', refresh_token);
    return response.data;
  }

  async logout() {
    await this.client.post('/api/v1/auth/logout');
    localStorage.removeItem('erin_access_token');
    localStorage.removeItem('erin_refresh_token');
  }

  async refreshSession() {
    return this.refreshAccessToken();
  }

  // Market Data
  async getQuotes(symbols: string[], fields?: string[]) {
    const params = new URLSearchParams();
    params.append('symbols', symbols.join(','));
    if (fields) params.append('fields', fields.join(','));
    const response = await this.client.get(`/api/v1/quotes?${params.toString()}`);
    return response.data;
  }

  async getQuoteHistory(symbol: string, start: string, end: string, interval: string, adjustment?: string) {
    const params = new URLSearchParams({
      start,
      end,
      interval,
    });
    if (adjustment) params.append('adjustment', adjustment);
    const response = await this.client.get(`/api/v1/quotes/${symbol}/history?${params.toString()}`);
    return response.data;
  }

  // Instruments
  async searchInstruments(query: string, assetClass?: string, exchange?: string, limit = 50) {
    const params = new URLSearchParams({
      search: query,
      limit: limit.toString(),
    });
    if (assetClass) params.append('asset_class', assetClass);
    if (exchange) params.append('exchange', exchange);
    const response = await this.client.get(`/api/v1/instruments?${params.toString()}`);
    return response.data;
  }

  async getInstrument(figi: string) {
    const response = await this.client.get(`/api/v1/instruments/${figi}`);
    return response.data;
  }

  // Watchlists
  async getWatchlists() {
    const response = await this.client.get('/api/v1/watchlists');
    return response.data;
  }

  async createWatchlist(name: string, symbols: string[] = []) {
    const response = await this.client.post('/api/v1/watchlists', { name, symbols });
    return response.data;
  }

  async getWatchlist(id: string) {
    const response = await this.client.get(`/api/v1/watchlists/${id}`);
    return response.data;
  }

  async updateWatchlist(id: string, data: { name?: string; symbols?: string[] }) {
    const response = await this.client.put(`/api/v1/watchlists/${id}`, data);
    return response.data;
  }

  async deleteWatchlist(id: string) {
    const response = await this.client.delete(`/api/v1/watchlists/${id}`);
    return response.data;
  }

  // Companies
  async searchCompanies(query: string, sector?: string, limit = 50) {
    const params = new URLSearchParams({
      search: query,
      limit: limit.toString(),
    });
    if (sector) params.append('sector', sector);
    const response = await this.client.get(`/api/v1/companies?${params.toString()}`);
    return response.data;
  }

  async getCompany(id: string) {
    const response = await this.client.get(`/api/v1/companies/${id}`);
    return response.data;
  }

  async getCompanyFinancials(id: string, params: {
    statement_type?: 'income' | 'balance_sheet' | 'cash_flow';
    period_type?: 'quarterly' | 'annual';
    limit?: number;
  } = {}) {
    const searchParams = new URLSearchParams();
    if (params.statement_type) searchParams.append('statement_type', params.statement_type);
    if (params.period_type) searchParams.append('period_type', params.period_type);
    if (params.limit) searchParams.append('limit', params.limit.toString());
    const response = await this.client.get(`/api/v1/companies/${id}/financials?${searchParams.toString()}`);
    return response.data;
  }

  async getCompanyRatios(id: string, periodEnd?: string, ratioType?: string) {
    const params = new URLSearchParams();
    if (periodEnd) params.append('period_end', periodEnd);
    if (ratioType) params.append('ratio_type', ratioType);
    const response = await this.client.get(`/api/v1/companies/${id}/ratios?${params.toString()}`);
    return response.data;
  }

  // Valuation
  async getValuationModels() {
    const response = await this.client.get('/api/v1/valuation/models');
    return response.data;
  }

  async runValuation(data: {
    model_id: string;
    company_id: string;
    as_of_date: string;
    inputs: Record<string, number>;
    sensitivity?: { variables: string[]; range_pct: number };
    scenarios?: Array<{ name: string; inputs: Record<string, number> }>;
  }) {
    const response = await this.client.post('/api/v1/valuation/runs', data);
    return response.data;
  }

  async getValuationRun(runId: string) {
    const response = await this.client.get(`/api/v1/valuation/runs/${runId}`);
    return response.data;
  }

  // Portfolio
  async getPortfolios() {
    const response = await this.client.get('/api/v1/portfolios');
    return response.data;
  }

  async createPortfolio(name: string, baseCurrency: string = 'USD') {
    const response = await this.client.post('/api/v1/portfolios', { name, base_currency: baseCurrency });
    return response.data;
  }

  async getPortfolio(id: string) {
    const response = await this.client.get(`/api/v1/portfolios/${id}`);
    return response.data;
  }

  async updatePortfolio(id: string, name: string) {
    const response = await this.client.put(`/api/v1/portfolios/${id}`, { name });
    return response.data;
  }

  async deletePortfolio(id: string) {
    const response = await this.client.delete(`/api/v1/portfolios/${id}`);
    return response.data;
  }

  async addPosition(portfolioId: string, figi: string, quantity: number, avgCost: number, currency: string) {
    const response = await this.client.post(`/api/v1/portfolios/${portfolioId}/positions`, {
      figi,
      quantity,
      avg_cost: avgCost,
      currency,
    });
    return response.data;
  }

  async removePosition(portfolioId: string, figi: string) {
    const response = await this.client.delete(`/api/v1/portfolios/${portfolioId}/positions/${figi}`);
    return response.data;
  }

  async addTransaction(portfolioId: string, data: {
    figi: string;
    side: 'BUY' | 'SELL';
    quantity: number;
    price: number;
    fees: number;
    executed_at: string;
    broker?: string;
  }) {
    const response = await this.client.post(`/api/v1/portfolios/${portfolioId}/transactions`, data);
    return response.data;
  }

  // Risk
  async getVarModels() {
    const response = await this.client.get('/api/v1/risk/var/models');
    return response.data;
  }

  async createVarModel(data: {
    name: string;
    method: 'HISTORICAL' | 'PARAMETRIC' | 'MONTE_CARLO';
    confidence_level: number;
    horizon_days: number;
    lookback_days?: number;
    distribution_assumption?: string;
    n_simulations?: number;
  }) {
    const response = await this.client.post('/api/v1/risk/var/models', data);
    return response.data;
  }

  async calculateVar(modelId: string, portfolioId: string, asOfDate: string) {
    const response = await this.client.post('/api/v1/risk/var/calculate', {
      model_id: modelId,
      portfolio_id: portfolioId,
      as_of_date: asOfDate,
    });
    return response.data;
  }

  async getVarResult(resultId: string) {
    const response = await this.client.get(`/api/v1/risk/var/results/${resultId}`);
    return response.data;
  }

  // Fixed Income
  async getBonds(params: { issuer?: string; rating?: string; limit?: number } = {}) {
    const params_ = new URLSearchParams();
    if (params.issuer) params_.append('issuer', params.issuer);
    if (params.rating) params_.append('rating', params.rating);
    if (params.limit) params_.append('limit', params.limit.toString());
    const response = await this.client.get(`/api/v1/fixed-income/bonds?${params_.toString()}`);
    return response.data;
  }

  async getBondAnalytics(figi: string, settlement: string, yield_?: number) {
    const params = new URLSearchParams({ settlement });
    if (yield_ !== undefined) params.append('yield', yield_.toString());
    const response = await this.client.get(`/api/v1/fixed-income/bonds/${figi}/analytics?${params.toString()}`);
    return response.data;
  }

  // Derivatives
  async getOptions(params: { underlying?: string; expiration?: string } = {}) {
    const params_ = new URLSearchParams();
    if (params.underlying) params_.append('underlying', params.underlying);
    if (params.expiration) params_.append('expiration', params.expiration);
    const response = await this.client.get(`/api/v1/derivatives/options?${params_.toString()}`);
    return response.data;
  }

  async priceOption(figi: string, params: {
    model: 'BSM' | 'BINOMIAL';
    spot: number;
    rate: number;
    vol: number;
    dividend_yield?: number;
  }) {
    const response = await this.client.get(`/api/v1/derivatives/options/${figi}/price`, { params });
    return response.data;
  }

  // Workspace
  async getNotebooks() {
    const response = await this.client.get('/api/v1/workspace/notebooks');
    return response.data;
  }

  async createNotebook(title: string, kernel: string = 'python3') {
    const response = await this.client.post('/api/v1/workspace/notebooks', { title, kernel });
    return response.data;
  }

  async getNotebook(id: string) {
    const response = await this.client.get(`/api/v1/workspace/notebooks/${id}`);
    return response.data;
  }

  async updateNotebook(id: string, cells: any[], version: number) {
    const response = await this.client.put(`/api/v1/workspace/notebooks/${id}`, { cells, version });
    return response.data;
  }

  async executeNotebookCell(notebookId: string, cellId: string, code: string) {
    const response = await this.client.post(`/api/v1/workspace/notebooks/${notebookId}/execute`, {
      cell_id: cellId,
      code,
    });
    return response.data;
  }

  // AI
  async queryRag(data: {
    query: string;
    index_id: string;
    top_k?: number;
    hybrid_weight?: number;
    filters?: Record<string, any>;
  }) {
    const response = await this.client.post('/api/v1/ai/rag/query', data);
    return response.data;
  }

  async executeTool(toolName: string, toolVersion: string, inputs: Record<string, any>) {
    const response = await this.client.post('/api/v1/ai/tools/execute', {
      tool_name: toolName,
      tool_version: toolVersion,
      inputs,
    });
    return response.data;
  }

  async getToolCall(callId: string) {
    const response = await this.client.get(`/api/v1/ai/tools/calls/${callId}`);
    return response.data;
  }

  async getTools() {
    const response = await this.client.get('/api/v1/ai/tools');
    return response.data;
  }
}

export const api = new ApiClient();
export default api;