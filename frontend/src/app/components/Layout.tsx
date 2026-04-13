import { Outlet, NavLink, useLocation } from "react-router";
import { Home, BarChart3, Settings, Battery, Wifi, Signal, SkipForward } from "lucide-react";
import { DemoPanel } from "./DemoPanel";
import { useAppContext } from "@/app/context/AppContext";

export function Layout() {
  const location = useLocation();
  const { dayOffset, nextDay } = useAppContext();

  const navItems = [
    { path: "/", icon: Home, label: "Home" },
    { path: "/insights", icon: BarChart3, label: "Insights" },
    { path: "/settings", icon: Settings, label: "Settings" },
  ];

  const now = new Date();
  now.setDate(now.getDate() + dayOffset);
  const timeString = now.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: false,
  });

  return (
    <div className="h-full flex items-stretch bg-gray-100 overflow-hidden pl-2">
      {/* Phone UI */}
      <div className="h-full w-full max-w-md flex-none flex flex-col bg-white relative">
        {/* Status Bar */}
        <div className="bg-white px-6 py-2 flex items-center justify-between text-sm border-b border-gray-100">
          <span className="font-medium">{timeString}</span>
          <div className="flex items-center gap-2">
            <Signal className="w-4 h-4" />
            <Wifi className="w-4 h-4" />
            <Battery className="w-4 h-4" />
          </div>
        </div>

        {/* Main Content — keyed by dayOffset so check-in resets each "day" */}
        <div key={dayOffset} className="flex-1 overflow-auto pb-20 bg-white">
          <Outlet />
        </div>

        {/* Bottom Navigation */}
        <nav className="fixed bottom-0 left-2 w-full max-w-md bg-white border-t border-lavender-100">
          <div className="flex justify-around items-center h-16">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.path === "/"
                  ? location.pathname === "/"
                  : location.pathname.startsWith(item.path);

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className="flex flex-col items-center justify-center flex-1 h-full gap-1"
                >
                  <div className={`p-1.5 rounded-xl transition-all ${isActive ? "bg-lavender-100" : ""}`}>
                    <Icon
                      className={`w-5 h-5 ${isActive ? "text-lavender-600" : "text-gray-400"}`}
                    />
                  </div>
                  <span className={`text-xs ${isActive ? "text-lavender-600 font-medium" : "text-gray-400"}`}>
                    {item.label}
                  </span>
                </NavLink>
              );
            })}
          </div>
        </nav>
      </div>

      {/* Center: Next Day button */}
      <div className="flex-none flex items-center justify-center px-6">
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={nextDay}
            className="flex flex-col items-center gap-2 bg-white hover:bg-lavender-50 active:bg-lavender-100 border border-gray-200 hover:border-lavender-300 text-gray-700 rounded-2xl px-5 py-4 transition-all group shadow-sm"
          >
            <SkipForward className="w-6 h-6 text-lavender-500 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-medium whitespace-nowrap">Next Day</span>
          </button>
          <span className="text-gray-400 text-xs font-mono">
            Day {dayOffset + 1}
          </span>
        </div>
      </div>

      {/* Right: Profile evolution panel */}
      <div className="flex-1 min-w-0 h-full">
        <DemoPanel />
      </div>
    </div>
  );
}
