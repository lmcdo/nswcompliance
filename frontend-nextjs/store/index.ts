import { configureStore } from '@reduxjs/toolkit';
import developmentReducer from './slices/developmentSlice';

export const store = configureStore({
 reducer: {
 development: developmentReducer,
 },
 middleware: (getDefaultMiddleware) =>
 getDefaultMiddleware({
 serializableCheck: {
 ignoredActions: ['persist/PERSIST'],
 },
 }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
