import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { DevelopmentType } from '@/components/development/types';

export interface DevelopmentState {
 types: DevelopmentType[];
 selected: DevelopmentType | null;
 loading: boolean;
 error: string | null;
 filters: {
 category?: string;
 zoning?: string;
 searchTerm?: string;
 };
}

const initialState: DevelopmentState = {
 types: [],
 selected: null,
 loading: false,
 error: null,
 filters: {},
};

export const fetchDevelopmentTypes = createAsyncThunk(
 'development/fetchTypes',
 async (params: { propertyId?: string; zoning?: string }) => {
 const searchParams = new URLSearchParams();
 if (params.propertyId) searchParams.append('propertyId', params.propertyId);
 if (params.zoning) searchParams.append('zoning', params.zoning);

 const response = await fetch(`/api/development-types?${searchParams}`);
 if (!response.ok) {
 throw new Error('Failed to fetch development types');
 }
 return response.json();
 }
);

const developmentSlice = createSlice({
 name: 'development',
 initialState,
 reducers: {
 setSelectedDevelopment: (state, action: PayloadAction<DevelopmentType | null>) => {
 state.selected = action.payload;
 },
 updateFilters: (state, action: PayloadAction<Partial<DevelopmentState['filters']>>) => {
 state.filters = { ...state.filters, ...action.payload };
 },
 clearSelection: (state) => {
 state.selected = null;
 },
 clearError: (state) => {
 state.error = null;
 },
 resetFilters: (state) => {
 state.filters = {};
 },
 },
 extraReducers: (builder) => {
 builder
 .addCase(fetchDevelopmentTypes.pending, (state) => {
 state.loading = true;
 state.error = null;
 })
 .addCase(fetchDevelopmentTypes.fulfilled, (state, action) => {
 state.loading = false;
 state.types = action.payload;
 })
 .addCase(fetchDevelopmentTypes.rejected, (state, action) => {
 state.loading = false;
 state.error = action.error.message || 'Failed to load development types';
 });
 },
});

export const {
 setSelectedDevelopment,
 updateFilters,
 clearSelection,
 clearError,
 resetFilters,
} = developmentSlice.actions;

export default developmentSlice.reducer;
