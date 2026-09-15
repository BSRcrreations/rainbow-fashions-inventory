// @vitest-environment jsdom
import 'fake-indexeddb/auto';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within, renderHook, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import VariantPicker from '../components/VariantPicker';
import PurchaseDetailPage from './PurchaseDetailPage';
import { useDraftAttachment } from '../hooks/useDraftAttachment';
import { api } from '../api/client';
import { draftKey, writeDraft } from '../utils/draftStorage';
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user: { id:'cert',store_id:'shop',role:'OWNER' } }) }));
vi.mock('../components/ToastProvider', () => ({ useToast: () => ({ success:vi.fn(),error:vi.fn() }) }));
vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<object>(), api: { get:vi.fn(),getBlob:vi.fn(),put:vi.fn(),post:vi.fn() } }));
beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); vi.mocked(api.get).mockResolvedValue([]); });
afterEach(cleanup);
function provider(child: React.ReactNode) { return <QueryClientProvider client={new QueryClient({ defaultOptions:{queries:{retry:false}} })}><MemoryRouter initialEntries={['/purchases/p1?edit=1']}>{child}</MemoryRouter></QueryClientProvider>; }
it('requires a conscious shared-barcode size choice before selecting inventory', async () => {
  const choose=vi.fn(); const user=userEvent.setup();
  const targets=['S','M','L','XL','2XL','3XL'].map(size => ({variant_id:size,product_id:'p1',product_name:'Twin Birds',size,current_stock:10}));
  vi.mocked(api.get).mockImplementation(async path => {
    if (path.includes('shared-targets')) return targets;
    if (path.includes('/variant/')) return {variant_id:'L',product_id:'p1',size:'L',available_stock:10,is_active:true,selling_price:'20'};
    if (path.includes('paginated')) return {items:[],total:0};
    return [];
  });
  render(provider(<VariantPicker onSelect={choose} />));
  await user.type(screen.getByRole('textbox',{name:'Scan or type barcode'}),'123456{Enter}');
  const dialog=await screen.findByRole('dialog');
  expect(choose).not.toHaveBeenCalled(); expect(within(dialog).getAllByRole('button').length).toBeGreaterThanOrEqual(6);
  await user.click(within(dialog).getByRole('button',{name:/^L Twin Birds/}));
  await waitFor(() => expect(choose).toHaveBeenCalledTimes(1));
  expect(choose.mock.calls[0][1].variant_id).toBe('L'); expect(api.post).not.toHaveBeenCalled();
});
it('restores all formal purchase fields after navigation and sends one atomic draft request', async () => {
  const key=draftKey({id:'cert',store_id:'shop'},'formal-purchase:p1');
  const base={id:'p1',version:2,status:'DRAFT',workflow_status:'DRAFT',supplier_name:'Supplier',invoice_number:'INV-1',purchase_date:'2026-09-12',items:[],audit_history:[],amount_paid:'0',packaging_amount:'0',freight_amount:'0',round_off:'0',currency:'INR'};
  const edited={...base,notes:'Keep this invoice note',invoice_number:'RECOVERED-2',items:[{id:'line',product_name:'Twin Birds',size:'L',color:'Black',unit:'Each',quantity:3,purchase_price:'10',list_unit_price:'10',line_total:'30',discount:'0',tax_rate:'0',tax_amount:'0',match_status:'MANUAL'}]};
  writeDraft(key,edited);
  vi.mocked(api.get).mockImplementation(async path => path==='/purchases/p1' ? base : []);
  vi.mocked(api.put).mockResolvedValue({...edited,version:3});
  render(provider(<Routes><Route path='/purchases/:purchaseId' element={<PurchaseDetailPage />} /></Routes>));
  expect(await screen.findByDisplayValue('RECOVERED-2')).toBeTruthy();
  expect(screen.getByDisplayValue('Keep this invoice note')).toBeTruthy();
  await userEvent.click(screen.getByRole('button',{name:'Save draft'}));
  await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1));
  const [path,body,headers]=vi.mocked(api.put).mock.calls[0];
  expect(path).toBe('/purchases/p1/draft'); expect(body).toMatchObject({header:{version:2,invoice_number:'RECOVERED-2',notes:'Keep this invoice note'},items:[{size:'L',quantity:3}]});
  expect(headers).toHaveProperty('Idempotency-Key'); expect(api.post).not.toHaveBeenCalled();
});
it('recovers photo bytes by account and removes them after upload', async () => {
  const key='cert-photo-'+crypto.randomUUID();
  let view=renderHook(() => useDraftAttachment(key));
  await waitFor(() => expect(view.result.current.busy).toBe(false));
  await act(async () => view.result.current.select(new File(['invoice-photo-content'],'invoice.png',{type:'image/png'})));
  view.unmount(); view=renderHook(() => useDraftAttachment(key));
  await waitFor(() => expect(view.result.current.file?.name).toBe('invoice.png'));
  const other=renderHook(() => useDraftAttachment(key+'-other-account'));
  await waitFor(() => expect(other.result.current.busy).toBe(false)); expect(other.result.current.file).toBe(null);
  await act(async () => view.result.current.select(null)); view.unmount();
  view=renderHook(() => useDraftAttachment(key)); await waitFor(() => expect(view.result.current.busy).toBe(false)); expect(view.result.current.file).toBe(null);
});
