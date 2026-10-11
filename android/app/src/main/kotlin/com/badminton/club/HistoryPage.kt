package com.badminton.club

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.badminton.club.core.Match
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val timeFmt = DateTimeFormatter.ofPattern("HH:mm")

private fun fmtTime(iso: String?): String =
    if (iso == null) "-" else LocalDateTime.parse(iso).format(timeFmt)

private fun fmtDuration(m: Match): String {
    val s = m.startedAt ?: return "-"
    val f = m.finishedAt ?: return "-"
    val seconds = Duration.between(LocalDateTime.parse(s), LocalDateTime.parse(f)).seconds
    return "%02d:%02d".format(seconds / 60, seconds % 60)
}

private fun joinDeltas(deltas: List<Pair<String, Double>>): String {
    val sep = if (Strings.lang == "zh") "，" else ", "
    return deltas.joinToString(sep) { (n, d) -> "$n ${"%+.1f".format(d)}" }
}

private enum class RangeOpt { ALL, TODAY, D7, D30, CUSTOM }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryPage(state: AppState) {
    val revision = state.revision
    val club = state.club

    var range by remember { mutableStateOf(RangeOpt.ALL) }
    var player by remember { mutableStateOf("") }
    var dateFrom by remember { mutableStateOf("") }
    var dateTo by remember { mutableStateOf("") }
    var showFrom by remember { mutableStateOf(false) }
    var showTo by remember { mutableStateOf(false) }

    val allMatches = remember(revision) { state.storage.loadMatches(club) }

    if (showFrom || showTo) {
        val target = if (showFrom) "from" else "to"
        val init = if (showFrom) {
            (if (dateFrom.isEmpty()) LocalDate.now().minusDays(30) else LocalDate.parse(dateFrom))
        } else {
            (if (dateTo.isEmpty()) LocalDate.now() else LocalDate.parse(dateTo))
        }
        val pickerState = rememberDatePickerState(
            initialSelectedDateMillis = init.atStartOfDay(ZoneId.of("UTC")).toInstant().toEpochMilli()
        )
        DatePickerDialog(
            onDismissRequest = { showFrom = false; showTo = false },
            confirmButton = {
                TextButton(onClick = {
                    pickerState.selectedDateMillis?.let {
                        val d = Instant.ofEpochMilli(it).atZone(ZoneId.of("UTC")).toLocalDate().toString()
                        if (target == "from") dateFrom = d else dateTo = d
                    }
                    showFrom = false
                    showTo = false
                }) { Text(T("create")) }
            },
        ) {
            DatePicker(state = pickerState)
        }
    }

    LazyColumn(modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
        item {
            Text(T("p_history"), style = MaterialTheme.typography.headlineSmall)
        }

        if (allMatches.isEmpty()) {
            item { Text(T("h_no_data"), color = MaterialTheme.colorScheme.outline) }
            return@LazyColumn
        }

        val namePool = allMatches.flatMap { it.names.values }.distinct().sorted()

        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    RangeButton(
                        label = T("h_range") + ": " + when (range) {
                            RangeOpt.ALL -> T("h_all")
                            RangeOpt.TODAY -> T("h_today")
                            RangeOpt.D7 -> T("h_7")
                            RangeOpt.D30 -> T("h_30")
                            RangeOpt.CUSTOM -> T("h_custom")
                        },
                        onClick = {
                            range = when (range) {
                                RangeOpt.ALL -> RangeOpt.TODAY
                                RangeOpt.TODAY -> RangeOpt.D7
                                RangeOpt.D7 -> RangeOpt.D30
                                RangeOpt.D30 -> RangeOpt.CUSTOM
                                RangeOpt.CUSTOM -> RangeOpt.ALL
                            }
                        },
                        modifier = Modifier.weight(1f),
                    )
                }
                if (range == RangeOpt.CUSTOM) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { showFrom = true }, modifier = Modifier.weight(1f)) {
                            Text("${T("h_from")}: ${dateFrom.ifEmpty { "-" }}")
                        }
                        OutlinedButton(onClick = { showTo = true }, modifier = Modifier.weight(1f)) {
                            Text("${T("h_to")}: ${dateTo.ifEmpty { "-" }}")
                        }
                    }
                    if (dateFrom.isNotEmpty() && dateTo.isNotEmpty() && dateFrom > dateTo) {
                        Text(T("h_range_invalid"), color = MaterialTheme.colorScheme.error)
                    }
                }
                PlayerMenu(
                    label = T("h_player") + ": " + player.ifEmpty { T("h_all_players") },
                    options = listOf(T("h_all_players")) + namePool,
                    selected = player.ifEmpty { T("h_all_players") },
                    onSelect = { player = it },
                )
            }
        }

        val today = LocalDate.now()
        val (fromIso, toIso) = when (range) {
            RangeOpt.ALL -> null to null
            RangeOpt.TODAY -> today.toString() to today.toString()
            RangeOpt.D7 -> today.minusDays(7).toString() to null
            RangeOpt.D30 -> today.minusDays(30).toString() to null
            RangeOpt.CUSTOM -> dateFrom.ifEmpty { null } to dateTo.ifEmpty { null }
        }

        val rows = allMatches
            .sortedWith(compareByDescending<Match> { it.date }.thenByDescending { it.seq })
            .filter { m ->
                if (fromIso != null && m.date < fromIso) return@filter false
                if (toIso != null && m.date > toIso) return@filter false
                if (player.isNotEmpty() && player != T("h_all_players") && player !in m.names.values) {
                    return@filter false
                }
                true
            }

        item {
            Text(
                T("h_count", "n" to rows.size),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )
        }

        if (rows.isEmpty()) {
            item { Text(T("h_no_data"), color = MaterialTheme.colorScheme.outline) }
        } else {
            items(rows, key = { it.id }) { m -> HistoryRow(m) }
        }
    }
}

@Composable
private fun RangeButton(label: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    OutlinedButton(onClick = onClick, modifier = modifier) { Text(label) }
}

@Composable
private fun PlayerMenu(
    label: String,
    options: List<String>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    OutlinedButton(onClick = { expanded = true }) {
        Text(label)
        androidx.compose.material3.DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            options.forEach { opt ->
                androidx.compose.material3.DropdownMenuItem(
                    text = { Text(opt) },
                    onClick = { onSelect(opt); expanded = false },
                )
            }
        }
    }
}

@Composable
private fun HistoryRow(m: Match) {
    val teamA = m.teamA.joinToString(" / ") { m.names[it] ?: it }
    val teamB = m.teamB.joinToString(" / ") { m.names[it] ?: it }
    val score = if (m.scoreA != null) "${m.scoreA}:${m.scoreB}" else T("ongoing")
    val winner = when (m.winner) {
        "A" -> T("team_a")
        "B" -> T("team_b")
        else -> "-"
    }
    val before = m.ratingsBefore
    val after = m.ratingsAfter
    val chg = if (!before.isNullOrEmpty() && !after.isNullOrEmpty()) {
        joinDeltas(
            before.map { (pid, r) ->
                (m.names[pid] ?: pid) to ((after[pid] ?: r) - r)
            }.sortedByDescending { it.second }
        )
    } else "-"

    Column(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        Row(modifier = Modifier.fillMaxWidth()) {
            Text(
                "${m.date} ${fmtTime(m.startedAt)}–${fmtTime(m.finishedAt)}",
                Modifier.weight(2f),
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "${T("h_court")} ${m.court}",
                Modifier.weight(1f),
                style = MaterialTheme.typography.labelMedium,
            )
            Text(
                T("board_${m.board}"),
                Modifier.weight(1.5f),
                style = MaterialTheme.typography.labelMedium,
            )
        }
        Row(modifier = Modifier.fillMaxWidth()) {
            Text(teamA, Modifier.weight(2f), style = MaterialTheme.typography.bodySmall)
            Text(score, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            Text(teamB, Modifier.weight(2f), style = MaterialTheme.typography.bodySmall)
        }
        Row(modifier = Modifier.fillMaxWidth()) {
            Text("${T("h_winner")}: $winner", Modifier.weight(1.5f), style = MaterialTheme.typography.labelSmall)
            Text(fmtDuration(m), Modifier.weight(1f), style = MaterialTheme.typography.labelSmall)
            Text(chg, Modifier.weight(3f), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
        }
    }
}
