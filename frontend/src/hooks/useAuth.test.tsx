// @vitest-environment jsdom
import { expect, it, vi, afterEach } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './useAuth';
import { api, ApiError } from '../api/client';
vi.mock('../api/client', async original => ({ ...await original<object>(), api:{me:vi.fn()} }));
afterEach(() => { cleanup();localStorage.clear();vi.clearAllMocks(); });
function Child(){const {user}=useAuth();return <p>{user?.full_name || 'Loading account'}</p>;}
it('keeps the sign-in and drafts on network failure and recovers without a password', async () => {
 localStorage.setItem('rainbow_inventory_token','test-only-token');localStorage.setItem('saved-draft','3 pieces');
 vi.mocked(api.me).mockRejectedValueOnce(new ApiError('Connection lost',0)).mockResolvedValueOnce({full_name:'Cashier'});
 render(<AuthProvider><Child /></AuthProvider>);
 await screen.findByText('Connection interrupted');expect(localStorage.getItem('rainbow_inventory_token')).toBe('test-only-token');
 await userEvent.click(screen.getByRole('button',{name:'Try again'}));await screen.findByText('Cashier');expect(localStorage.getItem('saved-draft')).toBe('3 pieces');
});
it('clears an expired token only when the server rejects authentication', async () => {
 localStorage.setItem('rainbow_inventory_token','test-only-token');vi.mocked(api.me).mockRejectedValueOnce(new ApiError('Expired',401));
 render(<AuthProvider><Child /></AuthProvider>);await waitFor(() => expect(localStorage.getItem('rainbow_inventory_token')).toBeNull());
});
