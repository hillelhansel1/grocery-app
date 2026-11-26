import { StyleSheet, Text } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

export default function App() {
  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.screen}>
        <Text accessibilityRole="header" style={styles.title}>
          קניות חכמות
        </Text>
        <Text style={styles.description}>ברוכים הבאים</Text>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#F4F7F1',
  },
  title: {
    color: '#173C2B',
    fontSize: 32,
    fontWeight: '700',
    textAlign: 'right',
    writingDirection: 'rtl',
  },
  description: {
    color: '#385749',
    fontSize: 18,
    marginTop: 8,
    textAlign: 'right',
    writingDirection: 'rtl',
  },
});
