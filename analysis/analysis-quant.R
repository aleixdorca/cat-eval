library(tidyverse)
library(RSQLite)
library(stringi)
library(kableExtra)
library(rstatix)

con_quant <- dbConnect(RSQLite::SQLite(), "../dbs/quant-eval.db")

rs1 <- dbSendQuery(con_quant, "SELECT * FROM content")
content_ca <- dbFetch(rs1)

rs2 <- dbSendQuery(con_quant, "SELECT * FROM grades")
grades_ca <- dbFetch(rs2)

content_ca <- content_ca %>% 
  rowwise() %>% 
  mutate(answer_length = length(unlist(strsplit(answer, "\\s+"))))

summary(aov(final_grade ~ model, data = content_ca))
tukey_hsd(content_ca %>% mutate(model = str_replace_all(model, "-", "_")), final_grade ~model) %>% 
  print(n = 100)

model_grade_ranking_ca <- content_ca %>% 
  group_by(model) %>% 
  summarise(model_grade = mean(final_grade),
            sd = sd(final_grade)) %>% 
  arrange(desc(model_grade)) %>% 
  rename(ca = model_grade,
         ca_sd = sd)

model_grade_ranking_ca %>% 
  arrange(desc(ca)) %>% 
  ungroup() %>% 
  mutate('#' = row_number() ) %>% 
  select('#', model, ca, ca_sd) %>%
  kable(round(2), format = "pipe")

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
  theme_minimal() +
  theme(legend.position = "none")

content_ca %>% 
  ggplot(aes(final_grade)) + 
  geom_histogram(aes(fill = model), color = "black") + 
  theme_minimal() +
  theme(legend.position = "none") +
  facet_wrap(~model)

content_ca %>% 
  ggplot(aes(final_grade, model)) + 
  geom_boxplot(aes(fill = model), alpha = 0.3) +
  geom_jitter(alpha = 0.2, height = 0.2) +
  scale_x_continuous(limits = c(7, 10), breaks = seq(0, 10, 1)) +
  theme_minimal() +
  theme(legend.position = "none")

grades_ca %>% 
  ggplot(aes(grade, evaluator)) + 
  geom_boxplot(aes(fill = evaluator), alpha = 0.2) + 
  geom_jitter(alpha = 0.2, height = 0.2) +
  scale_x_continuous(limits = c(0, 11), breaks = seq(0, 10, 1)) +
  theme_minimal() +
  theme(legend.position = "none")
