import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
  Switch,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

export default function CreateBinScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    bin_number: '',
    location: '',
    capacity: '',
    current_stock: '0',
    status: 'active',
    barcode: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.bin_number.trim()) {
      newErrors.bin_number = 'Bin number is required';
    }

    if (!formData.location.trim()) {
      newErrors.location = 'Location is required';
    }

    if (!formData.capacity || parseInt(formData.capacity) <= 0) {
      newErrors.capacity = 'Capacity must be greater than 0';
    }

    const stock = parseInt(formData.current_stock || '0');
    const capacity = parseInt(formData.capacity || '0');

    if (stock < 0) {
      newErrors.current_stock = 'Stock cannot be negative';
    }

    if (stock > capacity) {
      newErrors.current_stock = 'Stock cannot exceed capacity';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/bins`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          capacity: parseInt(formData.capacity),
          current_stock: parseInt(formData.current_stock || '0'),
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create bin');
      }

      Alert.alert('Success', 'Bin created successfully', [
        {
          text: 'OK',
          onPress: () => {
            setFormData({
              bin_number: '',
              location: '',
              capacity: '',
              current_stock: '0',
              status: 'active',
              barcode: '',
            });
            router.push('/bins');
          },
        },
      ]);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create bin');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({
      bin_number: '',
      location: '',
      capacity: '',
      current_stock: '0',
      status: 'active',
      barcode: '',
    });
    setErrors({});
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.formContainer}>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Bin Information</Text>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>
                Bin Number <Text style={styles.required}>*</Text>
              </Text>
              <View style={[styles.inputContainer, errors.bin_number && styles.inputError]}>
                <Ionicons name="cube" size={20} color="#8E8E93" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="e.g., BIN-001"
                  value={formData.bin_number}
                  onChangeText={(text) => {
                    setFormData({ ...formData, bin_number: text });
                    if (errors.bin_number) setErrors({ ...errors, bin_number: '' });
                  }}
                  placeholderTextColor="#C7C7CC"
                />
              </View>
              {errors.bin_number && <Text style={styles.errorText}>{errors.bin_number}</Text>}
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>
                Location <Text style={styles.required}>*</Text>
              </Text>
              <View style={[styles.inputContainer, errors.location && styles.inputError]}>
                <Ionicons name="location" size={20} color="#8E8E93" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="e.g., Aisle A, Row 1"
                  value={formData.location}
                  onChangeText={(text) => {
                    setFormData({ ...formData, location: text });
                    if (errors.location) setErrors({ ...errors, location: '' });
                  }}
                  placeholderTextColor="#C7C7CC"
                />
              </View>
              {errors.location && <Text style={styles.errorText}>{errors.location}</Text>}
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Barcode</Text>
              <View style={styles.inputContainer}>
                <Ionicons name="barcode" size={20} color="#8E8E93" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="e.g., 1234567890"
                  value={formData.barcode}
                  onChangeText={(text) => setFormData({ ...formData, barcode: text })}
                  placeholderTextColor="#C7C7CC"
                />
              </View>
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Capacity Details</Text>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>
                Maximum Capacity <Text style={styles.required}>*</Text>
              </Text>
              <View style={[styles.inputContainer, errors.capacity && styles.inputError]}>
                <Ionicons name="layers" size={20} color="#8E8E93" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="e.g., 1000"
                  value={formData.capacity}
                  onChangeText={(text) => {
                    setFormData({ ...formData, capacity: text.replace(/[^0-9]/g, '') });
                    if (errors.capacity) setErrors({ ...errors, capacity: '' });
                  }}
                  keyboardType="numeric"
                  placeholderTextColor="#C7C7CC"
                />
              </View>
              {errors.capacity && <Text style={styles.errorText}>{errors.capacity}</Text>}
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Current Stock</Text>
              <View style={[styles.inputContainer, errors.current_stock && styles.inputError]}>
                <Ionicons name="cube-outline" size={20} color="#8E8E93" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="e.g., 500"
                  value={formData.current_stock}
                  onChangeText={(text) => {
                    setFormData({ ...formData, current_stock: text.replace(/[^0-9]/g, '') });
                    if (errors.current_stock) setErrors({ ...errors, current_stock: '' });
                  }}
                  keyboardType="numeric"
                  placeholderTextColor="#C7C7CC"
                />
              </View>
              {errors.current_stock && <Text style={styles.errorText}>{errors.current_stock}</Text>}
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Status</Text>
            <View style={styles.switchRow}>
              <View>
                <Text style={styles.switchLabel}>Bin Status</Text>
                <Text style={styles.switchSubtext}>
                  {formData.status === 'active' ? 'Active' : 'Inactive'}
                </Text>
              </View>
              <Switch
                value={formData.status === 'active'}
                onValueChange={(value) =>
                  setFormData({ ...formData, status: value ? 'active' : 'inactive' })
                }
                trackColor={{ false: '#E5E5EA', true: '#34C759' }}
                thumbColor="#FFFFFF"
              />
            </View>
          </View>

          <View style={styles.buttonContainer}>
            <TouchableOpacity
              style={[styles.button, styles.secondaryButton]}
              onPress={handleReset}
              disabled={loading}
            >
              <Ionicons name="refresh" size={20} color="#007AFF" />
              <Text style={styles.secondaryButtonText}>Reset</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.button, styles.primaryButton, loading && styles.buttonDisabled]}
              onPress={handleSubmit}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={20} color="#FFFFFF" />
                  <Text style={styles.primaryButtonText}>Create Bin</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  scrollContent: {
    padding: 16,
  },
  formContainer: {
    gap: 16,
  },
  section: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000000',
    marginBottom: 16,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#3C3C43',
    marginBottom: 8,
  },
  required: {
    color: '#FF3B30',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F2F2F7',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#E5E5EA',
    paddingHorizontal: 12,
    height: 48,
  },
  inputError: {
    borderColor: '#FF3B30',
  },
  inputIcon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: '#000000',
  },
  errorText: {
    fontSize: 12,
    color: '#FF3B30',
    marginTop: 4,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  switchLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#000000',
  },
  switchSubtext: {
    fontSize: 14,
    color: '#8E8E93',
    marginTop: 2,
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
  button: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 10,
  },
  primaryButton: {
    backgroundColor: '#007AFF',
  },
  secondaryButton: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#007AFF',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
  },
});
