import { createContext, useContext, useState, type ReactNode } from "react";

interface AppContextType {
  dayOffset: number;
  nextDay: () => void;
}

const AppContext = createContext<AppContextType>({ dayOffset: 0, nextDay: () => {} });

export function AppProvider({ children }: { children: ReactNode }) {
  const [dayOffset, setDayOffset] = useState(0);
  return (
    <AppContext.Provider value={{ dayOffset, nextDay: () => setDayOffset((d) => d + 1) }}>
      {children}
    </AppContext.Provider>
  );
}

export const useAppContext = () => useContext(AppContext);
