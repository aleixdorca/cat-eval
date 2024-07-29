library(tidyverse)
library(RSQLite)
library(stringi)
library(kableExtra)
library(rstatix)

con_ca <- dbConnect(RSQLite::SQLite(), "cat-eval.db")

rs1 <- dbSendQuery(con_ca, "SELECT * FROM content")
content_ca <- dbFetch(rs1)

rs2 <- dbSendQuery(con_ca, "SELECT * FROM grades")
grades_ca <- dbFetch(rs2)

con_en <- dbConnect(RSQLite::SQLite(), "en-eval.db")

rs1 <- dbSendQuery(con_en, "SELECT * FROM content")
content_en <- dbFetch(rs1)

rs2 <- dbSendQuery(con_en, "SELECT * FROM grades")
grades_en <- dbFetch(rs2)

con_es <- dbConnect(RSQLite::SQLite(), "es-eval.db")

rs1 <- dbSendQuery(con_es, "SELECT * FROM content")
content_es <- dbFetch(rs1)

rs2 <- dbSendQuery(con_es, "SELECT * FROM grades")
grades_es <- dbFetch(rs2)

content_ca <- content_ca %>% 
  rowwise() %>% 
  mutate(model = ifelse(model == "aya:8b-23-f16", "aya:8b-23-fp16", model),
         model = ifelse(model == "mixtral:8x7b", "mixtral:8x7b-q4_0", model),
         answer_length = length(unlist(strsplit(answer, "\\s+"))),
         quant = stri_extract_last_regex(model, '.[0-9\\_]+'),
         quant = ifelse(quant == "x7", "q4_0", quant),
         quant = ifelse(quant == "p16", "fp16", quant),
         language = "ca")

content_en <- content_en %>% 
  rowwise() %>% 
  mutate(model = ifelse(model == "aya:8b-23-f16", "aya:8b-23-fp16", model),
         model = ifelse(model == "mixtral:8x7b", "mixtral:8x7b-q4_0", model),
         answer_length = length(unlist(strsplit(answer, "\\s+"))),
         quant = stri_extract_last_regex(model, '.[0-9\\_]+'),
         quant = ifelse(quant == "x7", "q4_0", quant),
         quant = ifelse(quant == "p16", "fp16", quant),
         language = "en")

content_es <- content_es %>% 
  rowwise() %>% 
  mutate(model = ifelse(model == "aya:8b-23-f16", "aya:8b-23-fp16", model),
         model = ifelse(model == "mixtral:8x7b", "mixtral:8x7b-q4_0", model),
         answer_length = length(unlist(strsplit(answer, "\\s+"))),
         quant = stri_extract_last_regex(model, '.[0-9\\_]+'),
         quant = ifelse(quant == "x7", "q4_0", quant),
         quant = ifelse(quant == "p16", "fp16", quant),
         language = "es")

summary(aov(final_grade ~model, data = content_ca))
tukey_hsd(content_ca %>% mutate(model = str_replace_all(model, "-", "_")), final_grade ~model) %>% 
  print(n = 100)

summary(aov(final_grade ~model, data = content_en))
tukey_hsd(content_en %>% mutate(model = str_replace_all(model, "-", "_")), final_grade ~model) %>% 
  print(n = 100)

summary(aov(final_grade ~model, data = content_es))
tukey_hsd(content_es %>% mutate(model = str_replace_all(model, "-", "_")), final_grade ~model) %>% 
  print(n = 100)

model_grade_ranking_ca <- content_ca %>% 
  group_by(model, quant) %>% 
  summarise(model_grade = mean(final_grade),
            sd = sd(final_grade)) %>% 
  arrange(desc(model_grade)) %>% 
  rename(ca = model_grade,
         ca_sd = sd)

model_grade_ranking_en <- content_en %>% 
  group_by(model) %>% 
  summarise(model_grade = mean(final_grade),
            sd = sd(final_grade)) %>% 
  arrange(desc(model_grade)) %>% 
  rename(en = model_grade,
         en_sd = sd)

model_grade_ranking_es <- content_es %>% 
  group_by(model) %>% 
  summarise(model_grade = mean(final_grade),
            sd = sd(final_grade)) %>% 
  arrange(desc(model_grade)) %>% 
  rename(es = model_grade,
         es_sd = sd)

model_grade_ranking_ca %>% 
  inner_join(model_grade_ranking_en, by = c("model")) %>% 
  inner_join(model_grade_ranking_es, by = c("model")) %>% 
  arrange(desc(ca)) %>% 
  ungroup() %>% 
  mutate('#' = row_number() ) %>% 
  select('#', model, ca, ca_sd, en, en_sd, es, es_sd) %>%
  kable(round(2), format = "pipe")

full_content <- content_ca %>% 
  bind_rows(content_en) %>% 
  bind_rows(content_es)

full_content %>% 
  group_by(model) %>% 
  t_test(final_grade ~ language) %>% 
  arrange(model, group1, group2) %>% 
  select(-.y., -n1, -n2, -p) %>% 
  rename(signif = p.adj.signif) %>% 
  kable(format = "pipe")

full_content %>% 
  ggplot(aes(x = language, y = final_grade)) +
  geom_boxplot(aes(fill = language), alpha = 0.6) +
  geom_jitter(alpha = 0.2, width = 0.2) +
  theme_minimal() +
  theme(legend.position = "bottom") +
  facet_wrap(~model)

full_content %>% 
  ggplot(aes(x = language, y = answer_length)) +
  geom_boxplot(aes(fill = language), alpha = 0.6) +
  geom_jitter(alpha = 0.2, width = 0.2) +
  theme_minimal() +
  theme(legend.position = "bottom") +
  facet_wrap(~model)

content_ca %>% 
  group_by(model) %>% 
  summarise(mean_length = mean(answer_length),
            sd = sd(answer_length)) %>% 
  arrange(desc(mean_length))

grades_ca %>% 
  group_by(evaluator) %>% 
  summarise(mean = mean(grade),
            sd = sd(grade)) %>% 
  arrange(desc(mean))

grades_ca %>% 
  ggplot(aes(grade)) + 
  geom_histogram(aes(fill = evaluator), color = "black", binwidth = 1) +
  facet_wrap(~evaluator) +
  scale_x_continuous(limits = c(0, 10), breaks = seq(0, 10, 1)) +
  lims(y = c(0, 500)) +
  theme_minimal() +
  theme(legend.position = "none")

content_ca %>% 
  ggplot(aes(final_grade)) + 
  geom_histogram(aes(fill = model), color = "black") + 
  scale_x_continuous(limits = c(0, 10), breaks = seq(0, 10, 1)) +
  theme_minimal() +
  theme(legend.position = "none") +
  facet_wrap(~model)

grades_ca %>% 
  ggplot(aes(grade, evaluator)) + 
  geom_boxplot(aes(fill = evaluator)) + 
  geom_jitter(alpha = 0.1, height = 0.2) +
  scale_x_continuous(limits = c(0, 11), breaks = seq(0, 10, 1)) +
  theme_minimal() +
  theme(legend.position = "none")
