import { useEffect, useState } from "react";
import { Wifi, WifiOff } from "lucide-react";

export default function ConnectionStatus() {
  const [online, setOnline] = useState(() => navigator.onLine);
  const [reconnected, setReconnected] = useState(false);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const lost = () => { setOnline(false); setReconnected(false); };
    const restored = () => { setOnline(true); setReconnected(true); timer = setTimeout(() => setReconnected(false), 6000); };
    window.addEventListener("offline", lost); window.addEventListener("online", restored);
    return () => { window.removeEventListener("offline", lost); window.removeEventListener("online", restored); clearTimeout(timer); };
  }, []);
  if (online && !reconnected) return null;
  return <div role="status" className={`flex items-center gap-3 px-4 py-3 text-base font-semibold ${online ? "bg-emerald-100 text-emerald-950" : "bg-amber-100 text-amber-950"}`}>{online ? <Wifi size={20} /> : <WifiOff size={20} />}{online ? "Connected again." : "Internet connection lost. Keep this page open; saved drafts remain on this device."}</div>;
}
