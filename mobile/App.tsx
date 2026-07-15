import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";
import { useState } from "react";
import { SafeAreaView, Text, TextInput, TouchableOpacity, View } from "react-native";


const queryClient = new QueryClient();


export default function App() {
  const [email, setEmail] = useState("Rainbow@fashions.com");
  const [password, setPassword] = useState("Fashions123");

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaView style={{ flex: 1, backgroundColor: "#f6f8fb" }}>
        <StatusBar style="dark" />
        <View style={{ flex: 1, padding: 20, justifyContent: "center" }}>
          <Text style={{ fontSize: 28, fontWeight: "700", color: "#0f172a" }}>Rainbow fashions</Text>
          <Text style={{ marginTop: 6, marginBottom: 24, color: "#64748b" }}>Inventory and billing for Android</Text>
          <TextInput
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
            placeholder="Email"
            style={{ height: 48, borderWidth: 1, borderColor: "#d9e2ec", borderRadius: 8, paddingHorizontal: 12, backgroundColor: "#fff", marginBottom: 12 }}
          />
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="Password"
            secureTextEntry
            style={{ height: 48, borderWidth: 1, borderColor: "#d9e2ec", borderRadius: 8, paddingHorizontal: 12, backgroundColor: "#fff", marginBottom: 16 }}
          />
          <TouchableOpacity style={{ height: 48, borderRadius: 8, backgroundColor: "#0f766e", alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: "#fff", fontWeight: "700" }}>Sign in</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </QueryClientProvider>
  );
}
