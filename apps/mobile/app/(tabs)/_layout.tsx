import { Tabs } from "expo-router";
import { Text, StyleSheet } from "react-native";

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  return (
    <Text
      style={[styles.tabIcon, focused && styles.tabIconFocused]}
      accessibilityRole="tab"
      accessibilityState={{ selected: focused }}
    >
      {label}
    </Text>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: "#F5F0EB" },
        headerTintColor: "#1C1917",
        tabBarActiveTintColor: "#D97706",
        tabBarInactiveTintColor: "#78716C",
        tabBarStyle: { backgroundColor: "#FAFAF9" },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ focused }) => (
            <TabIcon label="H" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="lessons"
        options={{
          title: "Lessons",
          tabBarIcon: ({ focused }) => (
            <TabIcon label="L" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="assignments"
        options={{
          title: "Assignments",
          tabBarIcon: ({ focused }) => (
            <TabIcon label="A" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="messages"
        options={{
          title: "Messages",
          tabBarIcon: ({ focused }) => (
            <TabIcon label="M" focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ focused }) => (
            <TabIcon label="P" focused={focused} />
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabIcon: {
    fontSize: 16,
    fontWeight: "600",
    color: "#78716C",
  },
  tabIconFocused: {
    color: "#D97706",
  },
});
