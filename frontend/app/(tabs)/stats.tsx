import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

interface Stats {
  total_bins: number;
  active_bins: number;
  inactive_bins: number;
  total_capacity: number;
  total_stock: number;
  utilization_percentage: number;
}

export default function StatsScreen() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bins/count`);
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
      Alert.alert('Error', 'Failed to load statistics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchStats();
  }, [fetchStats]);

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!stats) {
    return (
      <View style={styles.centerContainer}>
        <Ionicons name="stats-chart-outline" size={64} color="#C7C7CC" />
        <Text style={styles.emptyText}>No statistics available</Text>
      </View>
    );
  }

  const utilizationColor =
    stats.utilization_percentage >= 90
      ? '#FF3B30'
      : stats.utilization_percentage >= 70
      ? '#FF9500'
      : '#34C759';

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#007AFF" />
      }
    >
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="cube" size={24} color="#007AFF" />
          <Text style={styles.cardTitle}>Total Bins</Text>
        </View>
        <Text style={styles.statValue}>{stats.total_bins}</Text>
        <View style={styles.subStatsRow}>
          <View style={styles.subStat}>
            <View style={[styles.statusDot, { backgroundColor: '#34C759' }]} />
            <Text style={styles.subStatLabel}>Active</Text>
            <Text style={styles.subStatValue}>{stats.active_bins}</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.subStat}>
            <View style={[styles.statusDot, { backgroundColor: '#8E8E93' }]} />
            <Text style={styles.subStatLabel}>Inactive</Text>
            <Text style={styles.subStatValue}>{stats.inactive_bins}</Text>
          </View>
        </View>
      </View>

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="layers" size={24} color="#FF9500" />
          <Text style={styles.cardTitle}>Capacity</Text>
        </View>
        <Text style={styles.statValue}>{stats.total_capacity.toLocaleString()}</Text>
        <Text style={styles.statSubtext}>Total storage capacity</Text>
      </View>

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="cube-outline" size={24} color="#34C759" />
          <Text style={styles.cardTitle}>Current Stock</Text>
        </View>
        <Text style={styles.statValue}>{stats.total_stock.toLocaleString()}</Text>
        <Text style={styles.statSubtext}>Items in storage</Text>
      </View>

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="pie-chart" size={24} color={utilizationColor} />
          <Text style={styles.cardTitle}>Utilization</Text>
        </View>
        <View style={styles.utilizationContainer}>
          <Text style={[styles.utilizationValue, { color: utilizationColor }]}>
            {stats.utilization_percentage}%
          </Text>
          <View style={styles.progressBarContainer}>
            <View
              style={[
                styles.progressBar,
                {
                  width: `${Math.min(stats.utilization_percentage, 100)}%`,
                  backgroundColor: utilizationColor,
                },
              ]}
            />
          </View>
          <Text style={styles.utilizationText}>
            {stats.utilization_percentage < 50
              ? 'Low utilization - plenty of space available'
              : stats.utilization_percentage < 80
              ? 'Moderate utilization - good capacity usage'
              : stats.utilization_percentage < 95
              ? 'High utilization - consider expanding capacity'
              : 'Critical - near maximum capacity!'}
          </Text>
        </View>
      </View>

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="analytics" size={24} color="#5856D6" />
          <Text style={styles.cardTitle}>Quick Stats</Text>
        </View>
        <View style={styles.quickStatsGrid}>
          <View style={styles.quickStatItem}>
            <Text style={styles.quickStatValue}>
              {stats.total_bins > 0 ? Math.round(stats.total_capacity / stats.total_bins) : 0}
            </Text>
            <Text style={styles.quickStatLabel}>Avg Capacity/Bin</Text>
          </View>
          <View style={styles.quickStatItem}>
            <Text style={styles.quickStatValue}>
              {stats.total_bins > 0 ? Math.round(stats.total_stock / stats.total_bins) : 0}
            </Text>
            <Text style={styles.quickStatLabel}>Avg Stock/Bin</Text>
          </View>
          <View style={styles.quickStatItem}>
            <Text style={styles.quickStatValue}>
              {stats.total_capacity - stats.total_stock}
            </Text>
            <Text style={styles.quickStatLabel}>Available Space</Text>
          </View>
          <View style={styles.quickStatItem}>
            <Text style={styles.quickStatValue}>
              {stats.total_bins > 0
                ? Math.round((stats.active_bins / stats.total_bins) * 100)
                : 0}%
            </Text>
            <Text style={styles.quickStatLabel}>Active Rate</Text>
          </View>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  content: {
    padding: 16,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F2F2F7',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000000',
  },
  statValue: {
    fontSize: 48,
    fontWeight: '700',
    color: '#000000',
    marginBottom: 4,
  },
  statSubtext: {
    fontSize: 14,
    color: '#8E8E93',
  },
  subStatsRow: {
    flexDirection: 'row',
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E5EA',
  },
  subStat: {
    flex: 1,
    alignItems: 'center',
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginBottom: 8,
  },
  subStatLabel: {
    fontSize: 12,
    color: '#8E8E93',
    marginBottom: 4,
  },
  subStatValue: {
    fontSize: 24,
    fontWeight: '600',
    color: '#000000',
  },
  divider: {
    width: 1,
    backgroundColor: '#E5E5EA',
    marginHorizontal: 16,
  },
  utilizationContainer: {
    marginTop: 8,
  },
  utilizationValue: {
    fontSize: 48,
    fontWeight: '700',
    marginBottom: 12,
  },
  progressBarContainer: {
    height: 12,
    backgroundColor: '#E5E5EA',
    borderRadius: 6,
    overflow: 'hidden',
    marginBottom: 12,
  },
  progressBar: {
    height: '100%',
    borderRadius: 6,
  },
  utilizationText: {
    fontSize: 14,
    color: '#8E8E93',
    lineHeight: 20,
  },
  quickStatsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
    gap: 12,
  },
  quickStatItem: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#F2F2F7',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  quickStatValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#000000',
    marginBottom: 4,
  },
  quickStatLabel: {
    fontSize: 12,
    color: '#8E8E93',
    textAlign: 'center',
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#3C3C43',
    marginTop: 16,
  },
});
