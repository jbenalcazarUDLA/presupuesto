import React, { useEffect, useState } from 'react';
import { AuditLogItem } from '../types/budget';
import { formatCurrencyDisplay } from '../utils/math';

interface AuditModalProps {
  year: number;
  isOpen: boolean;
  onClose: () => void;
}

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

export const AuditModal: React.FC<AuditModalProps> = ({ year, isOpen, onClose }) => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchAuditLogs();
    }
  }, [isOpen, year]);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/budgets/${year}/audit?limit=200`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.items || []);
      }
    } catch (err) {
      console.error("Error al cargar auditoría:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const filteredLogs = logs.filter(item =>
    item.account_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.modified_by.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (item.reason && item.reason.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden border border-slate-200">
        
        {/* Cabecera del Modal */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-2.5">
            <span className="text-xl">📜</span>
            <div>
              <h2 className="text-base font-bold text-slate-800">
                Historial de Auditoría Presupuestaria — Año {year}
              </h2>
              <p className="text-xs text-slate-500">
                Registro inmutable de todas las modificaciones y justificaciones realizadas
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-lg font-bold p-1 rounded-lg hover:bg-slate-200 transition"
          >
            ✕
          </button>
        </div>

        {/* Buscador / Filtro */}
        <div className="px-6 py-3 bg-white border-b border-slate-100 flex items-center justify-between">
          <input
            type="text"
            placeholder="Filtrar por cuenta, usuario o motivo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 w-72 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <span className="text-xs text-slate-500 font-medium">
            Total registros: {filteredLogs.length}
          </span>
        </div>

        {/* Tabla de Registros */}
        <div className="overflow-y-auto flex-1 p-6">
          {loading ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              Cargando historial de cambios...
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              No se han registrado modificaciones para este año fiscal todavía.
            </div>
          ) : (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 font-semibold bg-slate-50/50">
                  <th className="py-2.5 px-3">Fecha y Hora</th>
                  <th className="py-2.5 px-3">Usuario</th>
                  <th className="py-2.5 px-3">Cuenta Presupuestada</th>
                  <th className="py-2.5 px-2">Mes</th>
                  <th className="py-2.5 px-3 text-right">Valor Anterior</th>
                  <th className="py-2.5 px-3 text-right">Valor Nuevo</th>
                  <th className="py-2.5 px-3">Motivo / Justificación</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {filteredLogs.map((log) => {
                  const dateStr = new Date(log.created_at).toLocaleString('es-EC', {
                    year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', second: '2-digit'
                  });

                  return (
                    <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px] whitespace-nowrap">
                        {dateStr}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-700">
                        <span className="bg-slate-100 px-2 py-0.5 rounded text-[11px] border border-slate-200">
                          {log.modified_by}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-medium text-slate-800">{log.account_name}</div>
                        <div className="text-[10px] text-slate-400">{log.category_name}</div>
                      </td>
                      <td className="py-2.5 px-2 text-slate-600 font-medium">
                        {MONTH_NAMES[log.month - 1] || `Mes ${log.month}`}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-500">
                        {formatCurrencyDisplay(log.previous_amount)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-indigo-700">
                        {formatCurrencyDisplay(log.new_amount)}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 text-[11px]">
                        {log.reason ? (
                          <span className="italic">{log.reason}</span>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Pie del Modal */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 px-4 py-2 rounded-lg border border-slate-300 shadow-sm transition"
          >
            Cerrar
          </button>
        </div>

      </div>
    </div>
  );
};
