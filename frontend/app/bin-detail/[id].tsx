import React, { useState, useEffect } from 'react';
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
import { useRouter, useLocalSearchParams, Stack } from 'expo-router';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

interface Bin {
  id: string;
  bin_number: string;
  location: string;
  capacity: number;
  current_stock: number;
  status: string;
  barcode: string;
  last_updated: string;
  created_at: string;
}

export default function BinDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [bin, setBin] = useState<Bin | null>(null);
  const [formData, setFormData] = useState({
    location: '',
    capacity: '',
    current_stock: '',
    status: 'active',
    barcode: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    fetchBin();
  }, [id]);

  const fetchBin = async () => {
    try {
      const response = await fetch(`${API_URL}/api/bins/${id}`);
      if (!response.ok) throw new Error('Failed to fetch bin');
      const data = await response.json();
      setBin(data);
      setFormData({
        location: data.location,
        capacity: data.capacity.toString(),
        current_stock: data.current_stock.toString(),
        status: data.status,
        barcode: data.barcode || '',
      });
    } catch (error) {
      console.error('Error fetching bin:', error);
      Alert.alert('Error', 'Failed to load bin details', [
        { text: 'Go Back', onPress: () => router.back() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

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

  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/bins/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          location: formData.location,
          capacity: parseInt(formData.capacity),
          current_stock: parseInt(formData.current_stock),
          status: formData.status,
          barcode: formData.barcode,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update bin');
      }

      const updatedBin = await response.json();
      setBin(updatedBin);
      setIsEditing(false);
      Alert.alert('Success', 'Bin updated successfully');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to update bin');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (bin) {
      setFormData({
        location: bin.location,
        capacity: bin.capacity.toString(),
        current_stock: bin.current_stock.toString(),
        status: bin.status,
        barcode: bin.barcode || '',
      });
    }
    setIsEditing(false);
    setErrors({});
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <Stack.Screen options={{ title: 'Loading...', headerShown: true }} />
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!bin) {
    return (
      <View style={styles.centerContainer}>
        <Stack.Screen options={{ title: 'Error', headerShown: true }} />
        <Ionicons name="alert-circle" size={64} color="#FF3B30" />
        <Text style={styles.errorText}>Bin not found</Text>
      </View>
    );
  }

  const utilizationPercent = (bin.current_stock / bin.capacity) * 100;
  const utilizationColor =
    utilizationPercent >= 90 ? '#FF3B30' : utilizationPercent >= 70 ? '#FF9500' : '#34C759';

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <Stack.Screen
        options={{
          title: bin.bin_number,
          headerShown: true,
          headerRight: () => (
            <TouchableOpacity
              onPress={() => setIsEditing(!isEditing)}
              disabled={saving}
            >
              <Text style={styles.headerButton}>
                {isEditing ? 'Cancel' : 'Edit'}
              </Text>
            </TouchableOpacity>
          ),
        }}
      />

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {!isEditing ? (
          <>
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="information-circle" size={24} color="#007AFF" />
                <Text style={styles.cardTitle}>Bin Information</Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Bin Number</Text>
                <Text style={styles.infoValue}>{bin.bin_number}</Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Location</Text>
                <Text style={styles.infoValue}>{bin.location}</Text>
              </View>

              {bin.barcode && (
                <View style={styles.infoRow}>
                  <Text style={styles.infoLabel}>Barcode</Text>
                  <Text style={styles.infoValue}>{bin.barcode}</Text>
                </View>
              )}

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Status</Text>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: bin.status === 'active' ? '#34C759' : '#8E8E93' },
                  ]}
                >
                  <Text style={styles.statusText}>{bin.status}</Text>
                </View>
              </View>
            </View>

            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="analytics" size={24} color="#FF9500" />
                <Text style={styles.cardTitle}>Capacity</Text>
              </View>

              <View style={styles.capacityDisplay}>
                <View style={styles.capacityStats}>
                  <View style={styles.capacityStat}>
                    <Text style={styles.capacityStatValue}>{bin.current_stock}</Text>
                    <Text style={styles.capacityStatLabel}>Current Stock</Text>
                  </View>
                  <Text style={styles.capacitySeparator}>/</Text>
                  <View style={styles.capacityStat}>
                    <Text style={styles.capacityStatValue}>{bin.capacity}</Text>
                    <Text style={styles.capacityStatLabel}>Max Capacity</Text>
                  </View>
                </View>

                <View style={styles.progressBarContainer}>
                  <View
                    style={[
                      styles.progressBar,
                      {
                        width: `${Math.min(utilizationPercent, 100)}%`,
                        backgroundColor: utilizationColor,
                      },
                    ]}
                  />
                </View>

                <View style={styles.utilizationRow}>
                  <Text style={[styles.utilizationText, { color: utilizationColor }]}>
                    {utilizationPercent.toFixed(1)}% Utilized
                  </Text>
                  <Text style={styles.availableText}>
                    {bin.capacity - bin.current_stock} available
                  </Text>
                </View>
              </View>
            </View>

            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="time" size={24} color="#5856D6" />
                <Text style={styles.cardTitle}>Timeline</Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Created</Text>
                <Text style={styles.infoValue}>
                  {new Date(bin.created_at).toLocaleDateString()}
                </Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Last Updated</Text>
                <Text style={styles.infoValue}>
                  {new Date(bin.last_updated).toLocaleDateString()}
                </Text>
              </View>
            </View>
          </>
        ) : (
          <>
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="create" size={24} color="#007AFF" />
                <Text style={styles.cardTitle}>Edit Bin</Text>
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
                onPress={handleCancel}
                disabled={saving}
              >
                <Ionicons name="close" size={20} color="#007AFF" />
                <Text style={styles.secondaryButtonText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.button, styles.primaryButton, saving && styles.buttonDisabled]}
                onPress={handleSave}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <>
                    <Ionicons name="checkmark-circle" size={20} color="#FFFFFF" />
                    <Text style={styles.primaryButtonText}>Save Changes</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F2F2F7',
  },
  scrollContent: {
    padding: 16,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000000',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F2F2F7',
  },
  infoLabel: {
    fontSize: 14,
    color: '#8E8E93',
    fontWeight: '500',
  },
  infoValue: {
    fontSize: 16,
    color: '#000000',
    fontWeight: '500',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FFFFFF',
    textTransform: 'uppercase',
  },
  capacityDisplay: {
    gap: 16,
  },
  capacityStats: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  capacityStat: {
    alignItems: 'center',
  },
  capacityStatValue: {
    fontSize: 32,
    fontWeight: '700',
    color: '#000000',
  },
  capacityStatLabel: {
    fontSize: 12,
    color: '#8E8E93',
    marginTop: 4,
  },
  capacitySeparator: {
    fontSize: 32,
    fontWeight: '300',
    color: '#C7C7CC',
  },
  progressBarContainer: {
    height: 12,
    backgroundColor: '#E5E5EA',
    borderRadius: 6,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    borderRadius: 6,
  },
  utilizationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  utilizationText: {
    fontSize: 16,
    fontWeight: '600',
  },
  availableText: {
    fontSize: 14,
    color: '#8E8E93',
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
    paddingVertical: 8,
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
  headerButton: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
    marginRight: 8,
  },
});
