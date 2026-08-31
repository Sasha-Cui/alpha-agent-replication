#!/usr/bin/env node

import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { pathToFileURL } from 'node:url'

function parseArgs(argv) {
  const output = {}
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index]
    const value = argv[index + 1]
    if (!key?.startsWith('--') || value === undefined) {
      throw new Error('arguments must be --name value pairs')
    }
    output[key.slice(2)] = value
  }
  for (const key of ['source', 'decisions', 'output', 'source-commit']) {
    if (!output[key]) throw new Error('missing --' + key)
  }
  return output
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex')
}

function selectedRows(snapshot, asset) {
  const rows = snapshot
    .filter(row => row?.agent_name === 'Fin_Analyst' && row?.asset === asset)
    .sort((left, right) => String(left.date).localeCompare(String(right.date)))
  if (asset === 'TSLA') {
    if (rows.length !== 47) throw new Error('unexpected TSLA row count: ' + rows.length)
    return rows
  }
  if (rows.length !== 55) throw new Error('unexpected BTC row count: ' + rows.length)
  return rows.slice(0, 50)
}

const args = parseArgs(process.argv.slice(2))
const sourcePath = path.resolve(args.source)
const decisionsPath = path.resolve(args.decisions)
const sourceBytes = fs.readFileSync(sourcePath)
const decisionBytes = fs.readFileSync(decisionsPath)
const snapshot = JSON.parse(decisionBytes.toString('utf8'))
if (!Array.isArray(snapshot) || snapshot.length !== 102) {
  throw new Error('official decision snapshot must contain 102 rows')
}

const {
  computeBuyHoldEquity,
  computeStrategyEquity,
  calculateMetricsFromSeries,
  computeWinRate,
} = await import(pathToFileURL(sourcePath))

const results = {}
for (const asset of ['TSLA', 'BTC']) {
  const rows = selectedRows(snapshot, asset)
  const assetType = asset === 'BTC' ? 'crypto' : 'stock'
  const equityWithFees = computeStrategyEquity(
    rows,
    100000,
    0.0006,
    'long_short',
    'aggressive',
  )
  const equityWithoutFees = computeStrategyEquity(
    rows,
    100000,
    0,
    'long_short',
    'aggressive',
  )
  const buyAndHoldEquity = computeBuyHoldEquity(rows, 100000)
  results[asset] = {
    decision_rows: rows.length,
    first_date: rows[0].date,
    last_date: rows.at(-1).date,
    first_id: rows[0].id,
    last_id: rows.at(-1).id,
    equity_with_fees: equityWithFees,
    equity_without_fees: equityWithoutFees,
    buy_and_hold_equity: buyAndHoldEquity,
    metrics_with_fees: calculateMetricsFromSeries(equityWithFees, assetType),
    metrics_without_fees: calculateMetricsFromSeries(equityWithoutFees, assetType),
    win_rate: computeWinRate(rows, 'long_short', 'aggressive'),
  }
}

const payload = {
  source_commit: args['source-commit'],
  source_path: 'src/lib/perf.js',
  source_sha256: sha256(sourceBytes),
  decision_snapshot_path: path.basename(decisionsPath),
  decision_snapshot_sha256: sha256(decisionBytes),
  decision_snapshot_rows: snapshot.length,
  selected_decision_rows: 97,
  excluded_post_window_btc_rows: 5,
  runtime: {
    node: process.version,
    platform: process.platform,
    architecture: process.arch,
  },
  configuration: {
    initial_capital: 100000,
    fee: 0.0006,
    slippage: 0.001,
    strategy: 'long_short',
    trading_mode: 'aggressive',
    stock_annual_days: 252,
    crypto_annual_days: 365,
  },
  network_calls: 0,
  results,
}

fs.writeFileSync(path.resolve(args.output), JSON.stringify(payload, null, 2) + '\n')
