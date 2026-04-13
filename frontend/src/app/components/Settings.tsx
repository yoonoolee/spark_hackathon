import { useEffect, useState } from "react";
import { ChevronRight, Bell, Moon, User, Calendar, Activity, HelpCircle, LogOut } from "lucide-react";
import { api } from "@/api/client";

const USER_ID = 1;

export function Settings() {
  const [userName, setUserName] = useState("Loading...");
  const [cycleLength, setCycleLength] = useState<number | null>(null);

  useEffect(() => {
    api.getUser(USER_ID).then((user) => {
      setUserName(user.name);
      setCycleLength(user.cycle_length_avg);
    }).catch((e) => console.error("Failed to fetch user:", e));
  }, []);

  const today = new Date();
  const dateString = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const settingsGroups = [
    {
      title: "Account",
      items: [
        { icon: User, label: "Profile", value: userName },
        { icon: Calendar, label: "Cycle Settings", value: cycleLength ? `${cycleLength} days` : "—" },
      ],
    },
    {
      title: "Preferences",
      items: [
        { icon: Bell, label: "Notifications", value: "Enabled" },
        { icon: Moon, label: "Dark Mode", value: "Off" },
        { icon: Activity, label: "Workout Reminders", value: "Daily" },
      ],
    },
    {
      title: "Support",
      items: [
        { icon: HelpCircle, label: "Help & FAQ" },
        { icon: LogOut, label: "Log Out" },
      ],
    },
  ];

  return (
    <div className="p-6 max-w-md mx-auto">
      <div className="mb-8">
        <p className="text-gray-500 text-sm mb-2">{dateString}</p>
        <h1 className="text-3xl">Settings</h1>
      </div>

      <div className="space-y-6">
        {settingsGroups.map((group, groupIndex) => (
          <div key={groupIndex}>
            <h2 className="text-sm text-gray-500 mb-3 px-2">{group.title}</h2>
            <div className="bg-white rounded-3xl shadow-sm border border-gray-200 overflow-hidden">
              {group.items.map((item, itemIndex) => {
                const Icon = item.icon;
                return (
                  <button
                    key={itemIndex}
                    className="w-full flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
                  >
                    <Icon className="w-5 h-5 text-lavender-400" />
                    <span className="flex-1 text-left">{item.label}</span>
                    {item.value && (
                      <span className="text-sm text-gray-400">{item.value}</span>
                    )}
                    <ChevronRight className="w-5 h-5 text-gray-300" />
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 text-center text-sm text-gray-400">
        <p>Version 1.0.0</p>
      </div>
    </div>
  );
}
